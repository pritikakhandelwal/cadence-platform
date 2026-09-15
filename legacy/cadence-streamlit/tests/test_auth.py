import hashlib
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from modules.auth import MAX_FAILED_ATTEMPTS, _verify_password, hash_password, login_user


class PasswordHashTests(unittest.TestCase):
    def test_argon2_hash_verifies_and_rejects_wrong_password(self):
        password_hash = hash_password("correct horse battery staple")

        self.assertTrue(password_hash.startswith("$argon2id$"))
        self.assertEqual(_verify_password(password_hash, "correct horse battery staple"), (True, False))
        self.assertEqual(_verify_password(password_hash, "wrong password"), (False, False))

    def test_legacy_sha256_hash_is_marked_for_upgrade(self):
        legacy_hash = hashlib.sha256(b"legacy password").hexdigest()

        self.assertEqual(_verify_password(legacy_hash, "legacy password"), (True, True))

    def test_successful_legacy_login_upgrades_the_hash(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "cadence.db"
            self._create_auth_tables(database_path)
            legacy_hash = hashlib.sha256(b"legacy password").hexdigest()
            connection = sqlite3.connect(database_path)
            try:
                connection.execute(
                    "INSERT INTO users(id, name, email, password, joined_on) VALUES (1, 'Test', 'test@example.com', ?, '2026-01-01')",
                    (legacy_hash,),
                )
                connection.commit()
            finally:
                connection.close()

            with patch("modules.auth.get_connection", side_effect=lambda: sqlite3.connect(database_path)):
                result = login_user("test@example.com", "legacy password")

            self.assertEqual(result.user[0], 1)
            connection = sqlite3.connect(database_path)
            try:
                stored_hash = connection.execute("SELECT password FROM users WHERE id = 1").fetchone()[0]
            finally:
                connection.close()
            self.assertTrue(stored_hash.startswith("$argon2id$"))

    def test_five_failed_attempts_lock_the_account_temporarily(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "cadence.db"
            self._create_auth_tables(database_path)
            with patch("modules.auth.get_connection", side_effect=lambda: sqlite3.connect(database_path)):
                for _ in range(MAX_FAILED_ATTEMPTS):
                    result = login_user("missing@example.com", "wrong password")
                locked_result = login_user("missing@example.com", "wrong password")

            self.assertEqual(result.error, "Invalid email or password.")
            self.assertIn("Too many login attempts", locked_result.error)

    @staticmethod
    def _create_auth_tables(database_path):
        connection = sqlite3.connect(database_path)
        try:
            connection.execute(
                "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, joined_on TEXT)"
            )
            connection.execute(
                "CREATE TABLE login_security(email TEXT PRIMARY KEY, failed_attempts INTEGER, locked_until TEXT, updated_at TEXT)"
            )
            connection.commit()
        finally:
            connection.close()

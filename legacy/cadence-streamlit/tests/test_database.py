"""Tests for database sanitization and query hardening."""

import unittest
import sqlite3
from modules.database import (
    get_connection,
    create_tables,
    save_analysis,
    get_user_analyses,
    get_user_statistics,
    get_similarity_history,
    get_achievement_data,
)


class DatabaseHardeningTests(unittest.TestCase):

    def setUp(self):
        create_tables()

    def test_database_connection_has_wal_and_foreign_keys(self):
        conn = get_connection()
        try:
            journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            foreign_keys = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            assert journal_mode.lower() == "wal"
            assert foreign_keys == 1
        finally:
            conn.close()

    def test_save_analysis_clamps_and_sanitizes_values(self):
        conn = get_connection()
        try:
            # Create dummy user
            conn.execute(
                "INSERT OR IGNORE INTO users (id, name, email, password) VALUES (999, 'Test', 'test999@db.com', 'dummy_hash')"
            )
            conn.commit()

            # Save with out-of-bounds similarity (>100) and negative distance
            save_analysis(999, 150.0, -5.0, "Great dance!")

            analyses = get_user_analyses(999)
            assert len(analyses) > 0
            similarity, dtw_distance, feedback, _ = analyses[0]
            # Similarity clamped to <= 100
            assert similarity == 100.0
            # Distance clamped to >= 0
            assert dtw_distance == 0.0
            assert feedback == "Great dance!"

            stats = get_user_statistics(999)
            total, best, avg, latest = stats
            assert total >= 1
            assert best <= 100.0

            achievements = get_achievement_data(999)
            assert achievements[0] >= 1

            history = get_similarity_history(999)
            assert len(history) >= 1
        finally:
            conn.execute("DELETE FROM analysis WHERE user_id = 999")
            conn.execute("DELETE FROM users WHERE id = 999")
            conn.commit()
            conn.close()

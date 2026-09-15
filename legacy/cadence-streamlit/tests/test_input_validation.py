"""Tests for modules.input_validation."""

import unittest

import pytest
from modules.input_validation import (
    validate_name,
    validate_email,
    validate_registration_fields,
)


class InputValidationTests(unittest.TestCase):

    # ------------------------------------------------------------------
    # Name
    # ------------------------------------------------------------------

    def test_empty_name_rejected(self):
        result = validate_name("")
        assert not result.ok
        assert result.error

    def test_name_too_long_rejected(self):
        result = validate_name("A" * 101)
        assert not result.ok

    def test_valid_name_accepted(self):
        result = validate_name("Alice Smith")
        assert result.ok

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------

    def test_missing_at_sign_rejected(self):
        result = validate_email("notanemail")
        assert not result.ok

    def test_missing_domain_rejected(self):
        result = validate_email("user@")
        assert not result.ok

    def test_missing_tld_rejected(self):
        result = validate_email("user@example")
        assert not result.ok

    def test_valid_email_accepted(self):
        result = validate_email("user@example.com")
        assert result.ok

    def test_email_normalised_to_lowercase(self):
        # validate_email itself does not mutate but should accept mixed case
        result = validate_email("User@Example.COM")
        assert result.ok

    def test_email_too_long_rejected(self):
        local = "a" * 244
        result = validate_email(f"{local}@example.com")  # > 254 chars
        assert not result.ok

    # ------------------------------------------------------------------
    # Registration fields
    # ------------------------------------------------------------------

    def test_passwords_mismatch_rejected(self):
        result = validate_registration_fields(
            "Alice", "a@b.com", "password123456", "different123456"
        )
        assert not result.ok

    def test_short_password_rejected(self):
        result = validate_registration_fields(
            "Alice", "a@b.com", "short", "short"
        )
        assert not result.ok

    def test_valid_registration_accepted(self):
        result = validate_registration_fields(
            "Alice Smith", "alice@example.com", "supersecure123", "supersecure123"
        )
        assert result.ok

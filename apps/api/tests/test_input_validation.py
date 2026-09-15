from __future__ import annotations

from app.security.input_validation import validate_email, validate_name, validate_registration_fields


def test_validate_name_rejects_empty():
    assert validate_name("   ").ok is False


def test_validate_name_rejects_too_long():
    assert validate_name("a" * 101).ok is False


def test_validate_email_rejects_malformed():
    assert validate_email("not-an-email").ok is False


def test_validate_email_accepts_normal_address():
    assert validate_email("person@example.com").ok is True


def test_validate_registration_rejects_mismatched_passwords():
    result = validate_registration_fields("Ada", "ada@example.com", "password-one", "password-two")
    assert result.ok is False
    assert "do not match" in result.error


def test_validate_registration_rejects_short_password():
    result = validate_registration_fields("Ada", "ada@example.com", "short", "short")
    assert result.ok is False


def test_validate_registration_accepts_valid_fields():
    result = validate_registration_fields(
        "Ada", "ada@example.com", "correct-horse-battery", "correct-horse-battery"
    )
    assert result.ok is True

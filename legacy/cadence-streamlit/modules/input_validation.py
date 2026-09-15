"""Input validation for user-supplied registration and login fields."""

from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

NAME_MIN = 1
NAME_MAX = 100

EMAIL_MIN = 5
EMAIL_MAX = 254          # RFC 5321 maximum

# Simple but robust RFC-5322 subset – rejects the most common attack payloads
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    error: str | None = None

    @classmethod
    def good(cls) -> "ValidationResult":
        return cls(ok=True)

    @classmethod
    def bad(cls, message: str) -> "ValidationResult":
        return cls(ok=False, error=message)


# ---------------------------------------------------------------------------
# Individual field validators
# ---------------------------------------------------------------------------

def validate_name(name: str) -> ValidationResult:
    """Ensure full name is present and within length bounds."""
    stripped = name.strip()
    if len(stripped) < NAME_MIN:
        return ValidationResult.bad("Please enter your full name.")
    if len(stripped) > NAME_MAX:
        return ValidationResult.bad(
            f"Name must be {NAME_MAX} characters or fewer."
        )
    return ValidationResult.good()


def validate_email(email: str) -> ValidationResult:
    """Ensure email is syntactically valid and within length bounds."""
    stripped = email.strip().lower()
    if len(stripped) < EMAIL_MIN:
        return ValidationResult.bad("Please enter a valid email address.")
    if len(stripped) > EMAIL_MAX:
        return ValidationResult.bad(
            f"Email must be {EMAIL_MAX} characters or fewer."
        )
    if not _EMAIL_RE.match(stripped):
        return ValidationResult.bad(
            "Please enter a valid email address (e.g. user@example.com)."
        )
    return ValidationResult.good()


# ---------------------------------------------------------------------------
# Compound validator for registration
# ---------------------------------------------------------------------------

def validate_registration_fields(
    name: str,
    email: str,
    password: str,
    confirm: str,
    password_minimum: int = 12,
) -> ValidationResult:
    """Validate all sign-up fields in one call.

    Returns the first error found, or a passing result if all fields are clean.
    """
    name_result = validate_name(name)
    if not name_result.ok:
        return name_result

    email_result = validate_email(email)
    if not email_result.ok:
        return email_result

    if password != confirm:
        return ValidationResult.bad("Passwords do not match.")

    if len(password) < password_minimum:
        return ValidationResult.bad(
            f"Password must be at least {password_minimum} characters."
        )

    return ValidationResult.good()

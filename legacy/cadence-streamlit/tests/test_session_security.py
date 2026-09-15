"""Tests for session security and HMAC integrity token."""

import unittest
from unittest.mock import patch
from modules.session_security import (
    _compute_token,
    stamp_session,
    verify_session,
    enforce_session_integrity,
)


class SessionSecurityTests(unittest.TestCase):

    def test_compute_token_is_deterministic_and_keyed(self):
        state1 = {"logged_in": True, "user": (1, "User", "u@e.com", "2026-01-01")}
        state2 = {"logged_in": True, "user": (1, "User", "u@e.com", "2026-01-01")}
        state3 = {"logged_in": True, "user": (2, "Other", "o@e.com", "2026-01-01")}

        token1 = _compute_token(state1)
        token2 = _compute_token(state2)
        token3 = _compute_token(state3)

        assert token1 == token2
        assert token1 != token3

    @patch("modules.session_security.st")
    def test_verify_session_returns_true_for_valid_token(self, mock_st):
        mock_st.session_state = {
            "logged_in": True,
            "user": (1, "User", "u@e.com", "2026-01-01"),
        }
        token = _compute_token(dict(mock_st.session_state))
        mock_st.session_state["_session_integrity_token"] = token

        assert verify_session() is True

    @patch("modules.session_security.st")
    def test_verify_session_detects_tampered_user(self, mock_st):
        mock_st.session_state = {
            "logged_in": True,
            "user": (1, "User", "u@e.com", "2026-01-01"),
        }
        token = _compute_token(dict(mock_st.session_state))
        mock_st.session_state["_session_integrity_token"] = token

        # Tamper user tuple to impersonate admin id 999
        mock_st.session_state["user"] = (999, "Admin", "admin@e.com", "2026-01-01")

        assert verify_session() is False

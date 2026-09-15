"""Session integrity helpers.

Streamlit's st.session_state is server-side memory and cannot be tampered with
by users over the network.  However, it can be corrupted by:
  - reloads after partial page errors leaving inconsistent keys
  - accidental overwrites from multi-page logic bugs

This module provides a lightweight HMAC-based integrity token so that any
inconsistency in the logged-in session is detected and cleared before the page
renders.  The secret is generated fresh at startup and lives only in-process,
so it provides no persistent security guarantee — it is a belt-and-braces
consistency check, not a cryptographic authentication layer.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import streamlit as st


# One-time in-process secret — regenerated every server restart.
_SESSION_SECRET: bytes = os.urandom(32)

_TOKEN_KEY = "_session_integrity_token"

# The subset of session keys that must be consistent when a user is logged in.
_PROTECTED_KEYS = ("logged_in", "user")


def _compute_token(session: dict) -> str:
    """Derive a token from the protected slice of session state."""
    payload = repr(
        {k: session.get(k) for k in _PROTECTED_KEYS}
    ).encode("utf-8")
    return hmac.new(_SESSION_SECRET, payload, hashlib.sha256).hexdigest()


def stamp_session() -> None:
    """Write (or refresh) the integrity token into session state.

    Call this immediately after mutating ``logged_in`` or ``user``.
    """
    st.session_state[_TOKEN_KEY] = _compute_token(dict(st.session_state))


def verify_session() -> bool:
    """Return True if the integrity token matches the current session state.

    Should be called at the top of each page render.  If it returns False the
    caller should clear session state and redirect the user to login.
    """
    token = st.session_state.get(_TOKEN_KEY)
    if token is None:
        # Guest / logged-out sessions have no token — that is fine.
        return not st.session_state.get("logged_in", False)

    expected = _compute_token(dict(st.session_state))
    return hmac.compare_digest(token, expected)


def enforce_session_integrity() -> bool:
    """Clear corrupted sessions and return whether the session is still valid.

    Typical usage at the top of app.py or any page entry point::

        if not enforce_session_integrity():
            st.warning("Your session expired. Please log in again.")
            st.stop()
    """
    if not verify_session():
        # Wipe everything to a clean slate.
        keys_to_clear = list(st.session_state.keys())
        for key in keys_to_clear:
            del st.session_state[key]
        return False
    return True

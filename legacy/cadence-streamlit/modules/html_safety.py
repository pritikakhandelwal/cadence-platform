"""Helpers for safely placing text inside trusted HTML templates."""

from html import escape


def escape_html(value: object) -> str:
    """Return text safe to interpolate into an HTML template."""

    return escape(str(value), quote=True)

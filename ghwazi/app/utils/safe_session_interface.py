"""
A thin wrapper around a SessionInterface that ensures cookie values are strings.
This prevents TypeError in Werkzeug when a bytes-like session_id is passed to
response.set_cookie by some session backends/signers.
"""
from __future__ import annotations

from typing import Any
import base64


class SafeCookieSessionInterface:
    """Proxy that coerces cookie value types to str on save_session.

    It wraps an existing SessionInterface (e.g., provided by Flask-Session)
    and intercepts response.set_cookie to ensure the cookie value is a str.
    """

    def __init__(self, base_interface: Any):
        self._base = base_interface

    def __getattr__(self, name: str) -> Any:
        # Delegate all other attributes/methods to the base interface
        return getattr(self._base, name)

    def save_session(self, app, session, response) -> None:
        # Intercept response.set_cookie to ensure value is str
        original_set_cookie = response.set_cookie

        def safe_set_cookie(key: str, value: Any, *args, **kwargs):
            if isinstance(value, (bytes, bytearray)):
                try:
                    value = value.decode("utf-8")
                except Exception:
                    # As a last resort, make it URL-safe base64 ascii
                    value = base64.urlsafe_b64encode(bytes(value)).decode("ascii")
            return original_set_cookie(key, value, *args, **kwargs)

        response.set_cookie = safe_set_cookie  # type: ignore[attr-defined]
        try:
            return self._base.save_session(app, session, response)
        finally:
            # Restore original method to avoid side effects
            response.set_cookie = original_set_cookie  # type: ignore[attr-defined]

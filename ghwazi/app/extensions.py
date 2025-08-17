"""
Flask extensions initialization.
"""

import os
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()


def _is_enabled() -> bool:
    """Determine if rate limiting should be enabled.
    - Disabled in testing if RATELIMIT_ENABLED env var is set to false or 0.
    - Enabled otherwise.
    """
    env_val = os.environ.get("RATELIMIT_ENABLED")
    if env_val is None:
        # Default: enabled
        return True
    return env_val.lower() in ("1", "true", "t", "yes", "y")


def create_limiter():
    """Create Flask-Limiter with appropriate storage backend.
    Uses Redis in production when REDISCLOUD_URL or REDIS_URL is provided,
    otherwise falls back to in-memory storage. Honors RATELIMIT_ENABLED.
    """
    enabled = _is_enabled()
    try:
        # Try to use Redis if available
        redis_url = os.environ.get('REDISCLOUD_URL') or os.environ.get('REDIS_URL')

        default_limits = [
            os.environ.get("RATELIMIT_PER_MINUTE", "100 per minute"),
            os.environ.get("RATELIMIT_PER_HOUR", "1000 per hour"),
        ]

        if redis_url:
            # Use Redis for rate limiting storage in distributed environments
            limiter = Limiter(
                key_func=get_remote_address,
                storage_uri=redis_url,
                default_limits=default_limits,
                enabled=enabled,
            )
            return limiter
        else:
            # Fallback to in-memory storage (suitable for dev/local)
            limiter = Limiter(
                key_func=get_remote_address,
                default_limits=default_limits,
                enabled=enabled,
            )
            return limiter

    except ImportError:
        # Redis not available, use in-memory storage
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[
                os.environ.get("RATELIMIT_PER_MINUTE", "100 per minute"),
                os.environ.get("RATELIMIT_PER_HOUR", "1000 per hour"),
            ],
            enabled=enabled,
        )
        return limiter


# Create the limiter instance
limiter = create_limiter()


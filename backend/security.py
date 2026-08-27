"""
security.py

Security utilities used across the app:
- Persistent random secret key (instead of a hardcoded constant)
- Simple in-memory rate limiting for login/register/reset endpoints
- CSRF token generation/validation for admin panel forms
- Shared input validators (password strength, email format, safe integers)

Standalone — no chatbot dependency.
"""

import os
import re
import time
import secrets
from collections import defaultdict


# ==============================================================
# Persistent secret key
# ==============================================================

SECRET_KEY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", ".secret_key"
)


def get_or_create_secret_key():
    """
    Loads a persisted random secret key, or generates and saves a new
    one on first run. This means Flask sessions survive server restarts
    (unlike a hardcoded key, which is predictable/insecure, or a
    randomly-regenerated-every-boot key, which would log everyone out
    on every restart).
    """

    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key

    if os.path.exists(SECRET_KEY_PATH):
        with open(SECRET_KEY_PATH, "r") as f:
            key = f.read().strip()
            if key:
                return key

    new_key = secrets.token_hex(32)
    os.makedirs(os.path.dirname(SECRET_KEY_PATH), exist_ok=True)
    with open(SECRET_KEY_PATH, "w") as f:
        f.write(new_key)

    return new_key


# ==============================================================
# Rate limiting (in-memory — fine for a single-process dev/college
# deployment; would need a shared store like Redis for multi-worker
# production deployment, noted honestly rather than pretending this
# scales infinitely)
# ==============================================================

_attempts = defaultdict(list)  # key -> list of failure timestamps

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutes


def _prune(key, window_seconds):
    cutoff = time.time() - window_seconds
    _attempts[key] = [t for t in _attempts[key] if t > cutoff]


def is_locked_out(key):
    _prune(key, LOCKOUT_SECONDS)
    return len(_attempts[key]) >= MAX_ATTEMPTS


def record_failed_attempt(key):
    _attempts[key].append(time.time())


def clear_attempts(key):
    _attempts[key] = []


def seconds_until_unlock(key):
    _prune(key, LOCKOUT_SECONDS)
    if not _attempts[key]:
        return 0
    oldest = min(_attempts[key])
    remaining = int(LOCKOUT_SECONDS - (time.time() - oldest))
    return max(0, remaining)


# ==============================================================
# CSRF tokens (applied to admin panel forms — see app.py)
# ==============================================================

def generate_csrf_token(session):
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(16)
    return session["_csrf_token"]


def validate_csrf_token(session, submitted_token):
    expected = session.get("_csrf_token")
    return bool(expected) and bool(submitted_token) and secrets.compare_digest(expected, submitted_token)


# ==============================================================
# Input validators
# ==============================================================

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LENGTH = 6


def is_valid_email(email):
    return bool(email) and bool(EMAIL_RE.match(email.strip()))


def is_strong_enough_password(password):
    return bool(password) and len(password) >= MIN_PASSWORD_LENGTH


def safe_positive_int(value, default=0, minimum=0, maximum=1_000_000):
    """
    Parses a form value into an int, clamped to [minimum, maximum].
    Never raises — returns `default` for anything unparseable, so a
    malformed or malicious value can't crash the request.
    """

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, parsed))

"""Authentication and Authorization Utilities for IP-SAKTI Sahayak.

Features:
- JWT token generation and validation.
- HttpOnly cookie management with SameSite and security flags.
- Password hashing via bcrypt.
- Login rate-limiting protection.
- `@login_required` route decorator enforcing user authentication.
"""
from __future__ import annotations
import logging
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

import jwt
from flask import g, jsonify, request

from config import (
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    JWT_ACCESS_TOKEN_EXPIRES_DAYS,
    JWT_ALGORITHM,
    JWT_SECRET_KEY
)
from models import User

logger = logging.getLogger(__name__)

COOKIE_NAME = "access_token"

# In-memory sliding window rate limiter for login protection
_login_failures: dict[str, list[float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 300  # 5 minutes


def is_rate_limited(ip_or_email: str) -> bool:
    """Check if the IP or email has exceeded max failed login attempts."""
    now = time.time()
    cutoff = now - LOCKOUT_WINDOW_SECONDS
    attempts = _login_failures.get(ip_or_email, [])
    # Keep only attempts within window
    recent = [t for t in attempts if t > cutoff]
    _login_failures[ip_or_email] = recent
    return len(recent) >= MAX_LOGIN_ATTEMPTS


def record_failed_attempt(ip_or_email: str):
    """Record a failed login attempt timestamp."""
    now = time.time()
    if ip_or_email not in _login_failures:
        _login_failures[ip_or_email] = []
    _login_failures[ip_or_email].append(now)


def clear_failed_attempts(ip_or_email: str):
    """Clear failed login attempts on successful login."""
    _login_failures.pop(ip_or_email, None)


def create_access_token(user: User) -> str:
    """Generate signed JWT token for authenticated user."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=JWT_ACCESS_TOKEN_EXPIRES_DAYS)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": user.full_name,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate signature and expiration of JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.debug("Access token expired")
        return None
    except jwt.InvalidTokenError as exc:
        logger.debug("Invalid access token: %s", exc)
        return None


def get_token_from_request() -> str | None:
    """Retrieve token from HttpOnly cookie or Authorization Bearer header."""
    # 1. Primary: HttpOnly cookie
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token

    # 2. Secondary: Authorization header Bearer token (for CLI/scripts)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


def set_auth_cookie(response, token: str):
    """Set secure HttpOnly cookie on response."""
    max_age = JWT_ACCESS_TOKEN_EXPIRES_DAYS * 24 * 3600
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/"
    )
    return response


def clear_auth_cookie(response):
    """Clear the authentication cookie."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE
    )
    return response


def login_required(f: Callable) -> Callable:
    """Decorator to protect routes requiring an authenticated user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({"error": "Authentication required. Please log in."}), 401

        payload = decode_access_token(token)
        if not payload or not payload.get("sub"):
            return jsonify({"error": "Invalid or expired session. Please log in again."}), 401

        user_id = int(payload["sub"])
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return jsonify({"error": "User account not found or deactivated."}), 401

        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function


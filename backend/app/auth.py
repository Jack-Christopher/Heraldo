"""
Authentication: JWT, password hashing, decorators.
"""
import functools
from typing import Optional

import bcrypt
import jwt
from flask import request, jsonify, g
from bson import ObjectId


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_token(user_id, secret_key: str, algorithm: str = "HS256", expires_seconds: int = 86400) -> str:
    """Create JWT access token."""
    from datetime import datetime, timedelta
    payload = {
        "sub": str(user_id),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(seconds=expires_seconds),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_token(token: str, secret_key: str, algorithm: str = "HS256") -> Optional[dict]:
    """Decode and validate JWT. Returns payload or None."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_from_request() -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return None


def get_current_user_id() -> Optional[ObjectId]:
    """Get current user ID from JWT (set by require_auth)."""
    return getattr(g, "user_id", None)


def require_auth(f):
    """Decorator to require JWT authentication."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        from flask import current_app
        token = get_token_from_request()
        if not token:
            return jsonify({"error": "Missing or invalid authorization"}), 401
        payload = decode_token(
            token,
            current_app.config["JWT_SECRET_KEY"],
            current_app.config.get("JWT_ALGORITHM", "HS256"),
        )
        if not payload or "sub" not in payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        try:
            g.user_id = ObjectId(payload["sub"])
        except Exception:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return wrapped


def require_admin(f):
    """Decorator to require JWT auth and admin role."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        from flask import current_app
        token = get_token_from_request()
        if not token:
            return jsonify({"error": "Missing or invalid authorization"}), 401
        payload = decode_token(
            token,
            current_app.config["JWT_SECRET_KEY"],
            current_app.config.get("JWT_ALGORITHM", "HS256"),
        )
        if not payload or "sub" not in payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        try:
            g.user_id = ObjectId(payload["sub"])
        except Exception:
            return jsonify({"error": "Invalid token"}), 401
        from ..models import user_find_by_id
        user = user_find_by_id(g.user_id)
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapped


def get_client_ip() -> str:
    """Get client IP from request (handles proxies)."""
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()

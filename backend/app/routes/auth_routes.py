"""
Auth routes: register, login, me.
"""
from flask import Blueprint, request, jsonify, current_app
from ..auth import hash_password, verify_password, create_token, get_client_ip, require_auth, get_current_user_id
from ..models import user_create, user_find_by_username, user_update_login, get_users_collection

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip() or None
    ip = get_client_ip()

    if not username or len(username) < 2:
        return jsonify({"error": "Username must be at least 2 characters"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if user_find_by_username(username):
        return jsonify({"error": "Username already exists"}), 409

    password_hash = hash_password(password)
    user = user_create(username=username, password_hash=password_hash, ip=ip, email=email)

    token = create_token(
        user["_id"],
        current_app.config["JWT_SECRET_KEY"],
        current_app.config.get("JWT_ALGORITHM", "HS256"),
        current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 86400),
    )
    return jsonify({
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user.get("email"),
        },
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    ip = get_client_ip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = user_find_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401

    user_update_login(user["_id"], ip)

    token = create_token(
        user["_id"],
        current_app.config["JWT_SECRET_KEY"],
        current_app.config.get("JWT_ALGORITHM", "HS256"),
        current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 86400),
    )
    return jsonify({
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user.get("email"),
        },
    })


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    user_id = get_current_user_id()
    user = get_users_collection().find_one({"_id": user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user.get("email"),
        "last_login": user.get("last_login").isoformat() if user.get("last_login") else None,
        "last_ip": user.get("last_ip"),
    })


@auth_bp.route("/change-password", methods=["POST"])
@require_auth
def change_password():
    data = request.get_json() or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not current_password:
        return jsonify({"error": "Current password required"}), 400
    if not new_password or len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    user_id = get_current_user_id()
    user = get_users_collection().find_one({"_id": user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not verify_password(current_password, user["password_hash"]):
        return jsonify({"error": "Current password is incorrect"}), 401

    get_users_collection().update_one(
        {"_id": user_id},
        {"$set": {"password_hash": hash_password(new_password)}}
    )
    return jsonify({"message": "Password updated"})

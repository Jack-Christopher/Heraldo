"""
Auth routes: register, login, me, verify-email.
"""
from flask import Blueprint, request, jsonify, current_app
from ..auth import hash_password, verify_password, create_token, get_client_ip, require_auth, get_current_user_id
from ..models import (
    user_create,
    user_find_by_email,
    user_find_by_ip,
    user_verify_email,
    user_update_login,
    get_users_collection,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    full_name = (data.get("full_name") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()
    ip = get_client_ip()

    if not full_name or len(full_name) < 2:
        return jsonify({"error": "Los nombres completos deben tener al menos 2 caracteres"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
    if not email or "@" not in email:
        return jsonify({"error": "El email es obligatorio"}), 400

    if user_find_by_email(email):
        return jsonify({"error": "El email ya está registrado"}), 409
    if user_find_by_ip(ip):
        return jsonify({"error": "No se pudo crear la cuenta. Intenta más tarde."}), 403

    password_hash = hash_password(password)
    user = user_create(full_name=full_name, password_hash=password_hash, ip=ip, email=email)
    user_update_login(user["_id"], ip)

    token = create_token(
        user["_id"],
        current_app.config["JWT_SECRET_KEY"],
        current_app.config.get("JWT_ALGORITHM", "HS256"),
        current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 86400),
    )
    return jsonify({
        "message": "Cuenta creada correctamente.",
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "full_name": user["full_name"],
            "email": user.get("email"),
            "role": user.get("role", "user"),
        },
    }), 201


@auth_bp.route("/verify-email", methods=["GET"])
def verify_email():
    token = request.args.get("token")
    if not token:
        return jsonify({"error": "Token de verificación requerido"}), 400
    user = user_find_by_verification_token(token)
    if not user:
        return jsonify({"error": "Token inválido o ya usado"}), 400
    user_verify_email(user["_id"])
    return jsonify({"message": "Email verificado. Ya puedes iniciar sesión."}), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    ip = get_client_ip()

    if not email or not password:
        return jsonify({"error": "Email y contraseña requeridos"}), 400

    user = user_find_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Credenciales inválidas"}), 401

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
            "full_name": user.get("full_name") or user.get("username", ""),
            "email": user.get("email"),
            "role": user.get("role", "user"),
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
        "full_name": user.get("full_name") or user.get("username", ""),
        "email": user.get("email"),
        "role": user.get("role", "user"),
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

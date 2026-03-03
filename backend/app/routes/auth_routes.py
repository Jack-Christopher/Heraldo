"""
Auth routes: register, login, me, verify-email.
"""
import uuid
from flask import Blueprint, request, jsonify, current_app
from ..auth import hash_password, verify_password, create_token, get_client_ip, require_auth, get_current_user_id
from ..models import (
    user_create,
    user_find_by_username,
    user_find_by_email,
    user_find_by_verification_token,
    user_verify_email,
    user_update_login,
    get_users_collection,
)

auth_bp = Blueprint("auth", __name__)


def _send_verification_email(email: str, verify_url: str) -> bool:
    """Send verification email. Returns True if sent, False if mail not configured."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        host = current_app.config.get("MAIL_SERVER")
        port = current_app.config.get("MAIL_PORT", 587)
        user = current_app.config.get("MAIL_USERNAME")
        password = current_app.config.get("MAIL_PASSWORD")
        from_addr = current_app.config.get("MAIL_FROM") or user or "noreply@heraldo.local"
        if not host or not user or not password:
            current_app.logger.warning("Mail not configured. Verification link: %s", verify_url)
            return False
        msg = MIMEMultipart()
        msg["Subject"] = "Confirma tu email - Heraldo"
        msg["From"] = from_addr
        msg["To"] = email
        body = f"""Hola,\n\nGracias por registrarte en Heraldo.\n\nConfirma tu correo haciendo clic en este enlace:\n{verify_url}\n\nSi no creaste esta cuenta, ignora este mensaje.\n"""
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [email], msg.as_string())
        return True
    except Exception as e:
        current_app.logger.exception("Failed to send verification email: %s", e)
        return False


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()
    ip = get_client_ip()

    if not username or len(username) < 2:
        return jsonify({"error": "El usuario debe tener al menos 2 caracteres"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
    if not email or "@" not in email:
        return jsonify({"error": "El email es obligatorio"}), 400

    if user_find_by_username(username):
        return jsonify({"error": "El nombre de usuario ya existe"}), 409
    if user_find_by_email(email):
        return jsonify({"error": "El email ya está registrado"}), 409

    verification_token = str(uuid.uuid4())
    password_hash = hash_password(password)
    user = user_create(
        username=username,
        password_hash=password_hash,
        ip=ip,
        email=email,
        verification_token=verification_token,
    )

    frontend_url = current_app.config.get("FRONTEND_URL") or request.url_root.rstrip("/")
    verify_url = f"{frontend_url.rstrip('/')}/verify?token={verification_token}"
    _send_verification_email(email, verify_url)

    return jsonify({
        "message": "Registro completado. Revisa tu email para confirmar la cuenta.",
        "email": email,
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
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    ip = get_client_ip()

    if not username or not password:
        return jsonify({"error": "Usuario y contraseña requeridos"}), 400

    user = user_find_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Credenciales inválidas"}), 401
    if not user.get("email_verified", True):
        return jsonify({"error": "Debes confirmar tu email antes de iniciar sesión. Revisa tu bandeja de entrada."}), 403

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

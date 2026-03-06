"""
Admin routes: list users, user detail, limits, documents. View PDFs and audios of any user.
"""
from flask import Blueprint, request, jsonify, current_app

from ..auth import require_admin, get_current_user_id
from ..models import (
    user_find_all,
    user_find_by_id,
    user_update_limits,
    user_get_effective_limits,
    document_find_by_user,
    document_find_by_id,
    document_count_active_by_user,
    document_count_total_by_user,
    get_documents_collection,
)

admin_bp = Blueprint("admin", __name__)


def _serialize_user(u, include_limits=False):
    data = {
        "id": str(u["_id"]),
        "full_name": u.get("full_name") or u.get("username", ""),
        "email": u.get("email"),
        "role": u.get("role", "user"),
        "created_at": u.get("created_at").isoformat() if u.get("created_at") else None,
        "last_login": u.get("last_login").isoformat() if u.get("last_login") else None,
    }
    if include_limits:
        global_max_pdfs = current_app.config.get("MAX_PDFS_PER_USER", 2)
        global_max_words = current_app.config.get("MAX_WORDS_PER_PDF", 1500)
        max_pdfs, max_words = user_get_effective_limits(u, global_max_pdfs, global_max_words)
        data["limits"] = u.get("limits") or {}
        data["effective_limits"] = {"max_pdfs_per_user": max_pdfs, "max_words_per_pdf": max_words}
    return data


@admin_bp.route("/users", methods=["GET"])
@require_admin
def list_users():
    """List all users."""
    limit = min(int(request.args.get("limit", 50)), 200)
    users = user_find_all(limit=limit)
    return jsonify([_serialize_user(u) for u in users])


@admin_bp.route("/users/<user_id>", methods=["GET"])
@require_admin
def get_user(user_id):
    """Get user detail with limits and document counts."""
    from bson import ObjectId
    try:
        uid = ObjectId(user_id)
    except Exception:
        return jsonify({"error": "Invalid user ID"}), 400
    user = user_find_by_id(uid)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = _serialize_user(user, include_limits=True)
    coll = get_documents_collection()
    data["stats"] = {
        "total_pdfs": document_count_total_by_user(uid),
        "active_pdfs": document_count_active_by_user(uid),
        "completed": coll.count_documents({"user_id": uid, "status": "completed"}),
        "pending": coll.count_documents({"user_id": uid, "status": "pending"}),
        "processing": coll.count_documents({"user_id": uid, "status": "processing"}),
        "failed": coll.count_documents({"user_id": uid, "status": "failed"}),
    }
    return jsonify(data)


@admin_bp.route("/users/<user_id>/limits", methods=["PATCH"])
@require_admin
def update_user_limits(user_id):
    """Update per-user limits."""
    from bson import ObjectId
    try:
        uid = ObjectId(user_id)
    except Exception:
        return jsonify({"error": "Invalid user ID"}), 400
    user = user_find_by_id(uid)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.get_json() or {}
    max_pdfs = data.get("max_pdfs_per_user")
    max_words = data.get("max_words_per_pdf")
    unset_max_pdfs = max_pdfs is None and "max_pdfs_per_user" in data
    unset_max_words = max_words is None and "max_words_per_pdf" in data
    if max_pdfs is not None and (not isinstance(max_pdfs, int) or max_pdfs < 0):
        return jsonify({"error": "max_pdfs_per_user must be a non-negative integer"}), 400
    if max_words is not None and (not isinstance(max_words, int) or max_words < 0):
        return jsonify({"error": "max_words_per_pdf must be a non-negative integer"}), 400
    user_update_limits(uid, max_pdfs, max_words, unset_max_pdfs=unset_max_pdfs, unset_max_words=unset_max_words)
    user = user_find_by_id(uid)
    return jsonify(_serialize_user(user, include_limits=True))


@admin_bp.route("/users/<user_id>/documents", methods=["GET"])
@require_admin
def list_user_documents(user_id):
    """List documents for a user (admin viewing)."""
    from bson import ObjectId
    try:
        uid = ObjectId(user_id)
    except Exception:
        return jsonify({"error": "Invalid user ID"}), 400
    user = user_find_by_id(uid)
    if not user:
        return jsonify({"error": "User not found"}), 404
    limit = min(int(request.args.get("limit", 50)), 200)
    docs = document_find_by_user(uid, limit=limit)
    result = []
    for d in docs:
        p = d.get("progress")
        result.append({
            "id": str(d["_id"]),
            "original_filename": d["original_filename"],
            "page_count": d.get("page_count"),
            "word_count": d.get("word_count"),
            "status": d["status"],
            "progress": {
                "phase": p.get("phase"),
                "current": p.get("current"),
                "total": p.get("total"),
                "pct": p.get("pct"),
                "label": p.get("label"),
            } if p else None,
            "created_at": d["created_at"].isoformat() if d.get("created_at") else None,
            "completed_at": d["completed_at"].isoformat() if d.get("completed_at") else None,
            "error_message": d.get("error_message"),
        })
    return jsonify(result)


@admin_bp.route("/users/<user_id>/documents/<doc_id>/play-token", methods=["POST"])
@require_admin
def admin_play_token(user_id, doc_id):
    """Admin: get play token for any user's document."""
    import jwt
    from datetime import datetime, timedelta
    from bson import ObjectId
    try:
        uid = ObjectId(user_id)
        doc_oid = ObjectId(doc_id)
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    doc = document_find_by_id(doc_oid)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if str(doc["user_id"]) != str(uid):
        return jsonify({"error": "Document does not belong to this user"}), 400
    if doc["status"] != "completed":
        return jsonify({"error": "Audio not ready yet"}), 400
    import os
    output_path = doc.get("output_path")
    if not output_path or not os.path.exists(output_path):
        return jsonify({"error": "Audio file not found"}), 404
    admin_id = get_current_user_id()
    payload = {
        "doc_id": str(doc_id),
        "sub": str(admin_id),
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config.get("JWT_ALGORITHM", "HS256"),
    )
    return jsonify({"token": token})


@admin_bp.route("/users/<user_id>/documents/<doc_id>/view-pdf-token", methods=["POST"])
@require_admin
def admin_view_pdf_token(user_id, doc_id):
    """Admin: get view PDF token for any user's document."""
    import jwt
    from datetime import datetime, timedelta
    from bson import ObjectId
    import os
    try:
        uid = ObjectId(user_id)
        doc_oid = ObjectId(doc_id)
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    doc = document_find_by_id(doc_oid)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if str(doc["user_id"]) != str(uid):
        return jsonify({"error": "Document does not belong to this user"}), 400
    pdf_path = doc.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "PDF file not found"}), 404
    admin_id = get_current_user_id()
    payload = {
        "doc_id": str(doc_id),
        "sub": str(admin_id),
        "view": "pdf",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config.get("JWT_ALGORITHM", "HS256"),
    )
    return jsonify({"token": token})

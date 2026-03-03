"""
User routes: stats for dashboard.
"""
from flask import Blueprint, jsonify
from datetime import datetime

from ..auth import require_auth, get_current_user_id
from ..models import get_documents_collection

user_bp = Blueprint("user", __name__)


@user_bp.route("/stats", methods=["GET"])
@require_auth
def stats():
    user_id = get_current_user_id()
    coll = get_documents_collection()

    total = coll.count_documents({"user_id": user_id})
    completed = coll.count_documents({"user_id": user_id, "status": "completed"})
    pending = coll.count_documents({"user_id": user_id, "status": "pending"})
    processing = coll.count_documents({"user_id": user_id, "status": "processing"})
    failed = coll.count_documents({"user_id": user_id, "status": "failed"})

    last_doc = coll.find_one(
        {"user_id": user_id},
        sort=[("created_at", -1)],
        projection={"original_filename": 1, "status": 1, "created_at": 1},
    )
    last_pdf_info = None
    if last_doc:
        last_pdf_info = {
            "filename": last_doc.get("original_filename"),
            "status": last_doc.get("status"),
            "created_at": last_doc["created_at"].isoformat() if last_doc.get("created_at") else None,
        }

    return jsonify({
        "total_pdfs": total,
        "completed": completed,
        "pending": pending,
        "processing": processing,
        "failed": failed,
        "last_pdf": last_pdf_info,
    })

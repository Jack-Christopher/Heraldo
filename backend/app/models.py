"""
MongoDB models and database access for Heraldo API.
"""
from datetime import datetime
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection


def get_db() -> Database:
    """Get MongoDB database connection (configured by app)."""
    from flask import current_app
    client = MongoClient(current_app.config["MONGODB_URI"])
    return client.get_default_database()


def get_users_collection() -> Collection:
    return get_db()["users"]


def get_documents_collection() -> Collection:
    return get_db()["documents"]


def user_create(full_name: str, password_hash: str, ip: str, email: str) -> dict:
    """Create a new user."""
    doc = {
        "full_name": full_name,
        "password_hash": password_hash,
        "email": email,
        "role": "user",
        "limits": {},
        "created_at": datetime.utcnow(),
        "last_login": datetime.utcnow(),
        "last_ip": ip,
        "created_from_ip": ip,
    }
    result = get_users_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def user_find_by_ip(ip: str) -> Optional[dict]:
    """Find user from this IP (one account per IP)."""
    return get_users_collection().find_one(
        {"$or": [{"created_from_ip": ip}, {"last_ip": ip}]}
    )


def user_find_by_verification_token(token: str) -> Optional[dict]:
    """Find user by verification token."""
    return get_users_collection().find_one({"verification_token": token})


def user_verify_email(user_id) -> None:
    """Mark user email as verified and clear token."""
    get_users_collection().update_one(
        {"_id": user_id},
        {"$set": {"email_verified": True}, "$unset": {"verification_token": ""}}
    )


def user_find_by_email(email: str) -> Optional[dict]:
    """Find user by email."""
    return get_users_collection().find_one({"email": email})


def user_find_by_id(user_id):
    """Find user by ID."""
    from bson import ObjectId
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    return get_users_collection().find_one({"_id": user_id})


def user_find_all(limit: int = 100) -> list:
    """List all users (for admin)."""
    return list(
        get_users_collection()
        .find({}, {"password_hash": 0})
        .sort("created_at", -1)
        .limit(limit)
    )


def user_update_limits(
    user_id,
    max_pdfs_per_user: Optional[int] = None,
    max_words_per_pdf: Optional[int] = None,
    unset_max_pdfs: bool = False,
    unset_max_words: bool = False,
) -> None:
    """Update per-user limits. Use unset_* to remove override (use global default)."""
    from bson import ObjectId
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    set_updates = {}
    unset_updates = {}
    if unset_max_pdfs:
        unset_updates["limits.max_pdfs_per_user"] = ""
    elif max_pdfs_per_user is not None:
        set_updates["limits.max_pdfs_per_user"] = max_pdfs_per_user
    if unset_max_words:
        unset_updates["limits.max_words_per_pdf"] = ""
    elif max_words_per_pdf is not None:
        set_updates["limits.max_words_per_pdf"] = max_words_per_pdf
    op = {}
    if set_updates:
        op["$set"] = set_updates
    if unset_updates:
        op["$unset"] = unset_updates
    if op:
        get_users_collection().update_one({"_id": user_id}, op)


def user_get_effective_limits(user_doc: Optional[dict], global_max_pdfs: int, global_max_words: int) -> tuple[int, int]:
    """Return (max_pdfs, max_words) for a user. Uses per-user limits if set, else global."""
    if not user_doc:
        return global_max_pdfs, global_max_words
    limits = user_doc.get("limits") or {}
    max_pdfs = limits.get("max_pdfs_per_user")
    max_words = limits.get("max_words_per_pdf")
    return (
        max_pdfs if max_pdfs is not None else global_max_pdfs,
        max_words if max_words is not None else global_max_words,
    )


def user_update_login(user_id, ip: str):
    """Update last login and IP."""
    get_users_collection().update_one(
        {"_id": user_id},
        {"$set": {"last_login": datetime.utcnow(), "last_ip": ip}}
    )


def document_create(user_id, original_filename: str, page_count: int, word_count: int, pdf_path: str) -> dict:
    """Create a document record (status: pending)."""
    doc = {
        "user_id": user_id,
        "original_filename": original_filename,
        "page_count": page_count,
        "word_count": word_count,
        "pdf_path": pdf_path,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "output_path": None,
        "error_message": None,
        "completed_at": None,
    }
    result = get_documents_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def document_update_status(doc_id, status: str, output_path: Optional[str] = None, error_message: Optional[str] = None):
    """Update document status."""
    update = {"status": status}
    if output_path is not None:
        update["output_path"] = output_path
    if error_message is not None:
        update["error_message"] = error_message
    if status in ("completed", "failed"):
        update["completed_at"] = datetime.utcnow()
        update["progress"] = None  # clear progress when done
    get_documents_collection().update_one({"_id": doc_id}, {"$set": update})


def document_update_progress(doc_id, phase: str, current: int, total: int, phase_label: str = "", overall_pct: float = None):
    """Update processing progress. overall_pct = 0-100 for total pipeline progress."""
    step_pct = round(100 * current / total, 1) if total > 0 else 0
    if overall_pct is None:
        overall_pct = step_pct
    get_documents_collection().update_one(
        {"_id": doc_id},
        {"$set": {"progress": {
            "phase": phase,
            "current": current,
            "total": total,
            "pct": overall_pct,
            "label": phase_label,
        }}}
    )


def document_find_by_id(doc_id):
    """Find document by ID (returns ObjectId or string)."""
    from bson import ObjectId
    if isinstance(doc_id, str):
        doc_id = ObjectId(doc_id)
    return get_documents_collection().find_one({"_id": doc_id})


def document_find_by_user(user_id, limit: int = 50):
    """List documents for a user, newest first."""
    return list(
        get_documents_collection()
        .find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(limit)
    )


def document_count_active_by_user(user_id) -> int:
    """Count documents with status pending or processing (for quota)."""
    return get_documents_collection().count_documents(
        {"user_id": user_id, "status": {"$in": ["pending", "processing"]}}
    )


def document_count_total_by_user(user_id) -> int:
    """Count all documents for a user (for total limit)."""
    return get_documents_collection().count_documents({"user_id": user_id})

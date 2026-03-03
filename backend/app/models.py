"""
MongoDB models and database access for Heraldo API.
"""
from datetime import datetime
from typing import Optional
from pymongo import MongoClient, ASCENDING
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


def ensure_indexes(db: Database):
    """Create required indexes."""
    db.users.create_index("username", unique=True)
    db.documents.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])


def user_create(username: str, password_hash: str, ip: str, email: Optional[str] = None) -> dict:
    """Create a new user."""
    doc = {
        "username": username,
        "password_hash": password_hash,
        "email": email,
        "created_at": datetime.utcnow(),
        "last_login": datetime.utcnow(),
        "last_ip": ip,
    }
    result = get_users_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def user_find_by_username(username: str) -> Optional[dict]:
    """Find user by username."""
    return get_users_collection().find_one({"username": username})


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
    get_documents_collection().update_one({"_id": doc_id}, {"$set": update})


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

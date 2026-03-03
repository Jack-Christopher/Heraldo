"""
PDF routes: upload, list, status, download, stream.
"""
import os
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from bson import ObjectId
import jwt

from ..auth import require_auth, get_current_user_id
from ..models import (
    document_create,
    document_find_by_id,
    document_find_by_user,
    document_count_active_by_user,
    document_count_total_by_user,
    get_documents_collection,
)
from ..services.pdf_service import validate_pdf_limits, count_pdf_pages_and_words
from ..worker import enqueue_document, start_worker

pdf_bp = Blueprint("pdf", __name__)

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@pdf_bp.route("/count-words", methods=["POST"])
@require_auth
def count_words():
    """Pre-validate: count words in PDF without saving. Returns word_count and within_limit."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    import uuid
    uploads_dir = current_app.config["UPLOADS_DIR"]
    user_id = get_current_user_id()
    user_uploads = os.path.join(uploads_dir, str(user_id))
    os.makedirs(user_uploads, exist_ok=True)
    temp_path = os.path.join(user_uploads, f"_count_{uuid.uuid4()}.pdf")
    try:
        file.save(temp_path)
        _, word_count = count_pdf_pages_and_words(temp_path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 400
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    max_words = current_app.config["MAX_WORDS_PER_PDF"]
    return jsonify({
        "word_count": word_count,
        "max_words": max_words,
        "within_limit": word_count <= max_words,
    })


@pdf_bp.route("/upload", methods=["POST"])
@require_auth
def upload():
    user_id = get_current_user_id()
    max_pdfs = current_app.config["MAX_PDFS_PER_USER"]
    max_words = current_app.config["MAX_WORDS_PER_PDF"]

    # Check total limit (max PDFs per user in account)
    total_count = document_count_total_by_user(user_id)
    if total_count >= max_pdfs:
        return jsonify({"error": f"Has alcanzado el límite de {max_pdfs} PDFs. No puedes subir más."}), 400

    # Check concurrent limit (max in process at once)
    active_count = document_count_active_by_user(user_id)
    if active_count >= max_pdfs:
        return jsonify({"error": f"Máximo {max_pdfs} PDFs en proceso. Espera a que terminen."}), 400

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are allowed"}), 400

    filename = secure_filename(file.filename)
    uploads_dir = current_app.config["UPLOADS_DIR"]
    user_uploads = os.path.join(uploads_dir, str(user_id))
    os.makedirs(user_uploads, exist_ok=True)

    # Save temporarily
    import uuid
    temp_id = str(uuid.uuid4())
    pdf_path = os.path.join(user_uploads, f"{temp_id}.pdf")
    file.save(pdf_path)

    # Validate limits (word count only)
    valid, err_msg, page_count, word_count = validate_pdf_limits(pdf_path, max_words)
    if not valid:
        os.remove(pdf_path)
        return jsonify({"error": err_msg, "page_count": page_count, "word_count": word_count}), 400

    # Create document record
    doc = document_create(
        user_id=user_id,
        original_filename=filename,
        page_count=page_count,
        word_count=word_count,
        pdf_path=pdf_path,
    )

    # Rename PDF to use doc id for clarity
    final_pdf_path = os.path.join(user_uploads, f"{doc['_id']}.pdf")
    os.rename(pdf_path, final_pdf_path)
    get_documents_collection().update_one(
        {"_id": doc["_id"]},
        {"$set": {"pdf_path": final_pdf_path}}
    )
    doc["pdf_path"] = final_pdf_path

    # Enqueue for processing
    start_worker(current_app._get_current_object())
    enqueue_document(doc["_id"])

    return jsonify({
        "id": str(doc["_id"]),
        "original_filename": filename,
        "page_count": page_count,
        "word_count": word_count,
        "status": "pending",
    }), 201


@pdf_bp.route("", methods=["GET"])
@require_auth
def list_documents():
    user_id = get_current_user_id()
    docs = document_find_by_user(user_id)
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


@pdf_bp.route("/<doc_id>/status", methods=["GET"])
@require_auth
def get_status(doc_id):
    user_id = get_current_user_id()
    try:
        doc = document_find_by_id(doc_id)
    except Exception:
        return jsonify({"error": "Invalid document ID"}), 400

    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if str(doc["user_id"]) != str(user_id):
        return jsonify({"error": "Forbidden"}), 403

    return jsonify({
        "id": str(doc["_id"]),
        "status": doc["status"],
        "error_message": doc.get("error_message"),
        "completed_at": doc["completed_at"].isoformat() if doc.get("completed_at") else None,
    })


@pdf_bp.route("/<doc_id>/download", methods=["GET"])
@require_auth
def download(doc_id):
    user_id = get_current_user_id()
    try:
        doc = document_find_by_id(doc_id)
    except Exception:
        return jsonify({"error": "Invalid document ID"}), 400

    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if str(doc["user_id"]) != str(user_id):
        return jsonify({"error": "Forbidden"}), 403
    if doc["status"] != "completed":
        return jsonify({"error": "Audio not ready yet"}), 400

    output_path = doc.get("output_path")
    if not output_path or not os.path.exists(output_path):
        return jsonify({"error": "Audio file not found"}), 404

    filename = os.path.basename(output_path)
    return send_file(output_path, as_attachment=True, download_name=filename)


@pdf_bp.route("/<doc_id>/play-token", methods=["POST"])
@require_auth
def play_token(doc_id):
    """Get short-lived token for streaming audio (no full download)."""
    user_id = get_current_user_id()
    try:
        doc = document_find_by_id(doc_id)
    except Exception:
        return jsonify({"error": "Invalid document ID"}), 400
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if str(doc["user_id"]) != str(user_id):
        return jsonify({"error": "Forbidden"}), 403
    if doc["status"] != "completed":
        return jsonify({"error": "Audio not ready yet"}), 400
    output_path = doc.get("output_path")
    if not output_path or not os.path.exists(output_path):
        return jsonify({"error": "Audio file not found"}), 404

    payload = {"doc_id": str(doc_id), "sub": str(user_id), "exp": datetime.utcnow() + timedelta(hours=1)}
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config.get("JWT_ALGORITHM", "HS256"),
    )
    return jsonify({"token": token})


@pdf_bp.route("/<doc_id>/view-pdf-token", methods=["POST"])
@require_auth
def view_pdf_token(doc_id):
    """Get short-lived token for viewing the uploaded PDF."""
    user_id = get_current_user_id()
    try:
        doc = document_find_by_id(doc_id)
    except Exception:
        return jsonify({"error": "Invalid document ID"}), 400
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if str(doc["user_id"]) != str(user_id):
        return jsonify({"error": "Forbidden"}), 403
    pdf_path = doc.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "PDF file not found"}), 404

    payload = {"doc_id": str(doc_id), "sub": str(user_id), "view": "pdf", "exp": datetime.utcnow() + timedelta(hours=1)}
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config.get("JWT_ALGORITHM", "HS256"),
    )
    return jsonify({"token": token})


@pdf_bp.route("/<doc_id>/view", methods=["GET"])
def view_pdf(doc_id):
    """Serve the uploaded PDF for in-browser viewing (new tab)."""
    token = request.args.get("t")
    if not token:
        return jsonify({"error": "Missing view token"}), 401
    secret = current_app.config["JWT_SECRET_KEY"]
    algo = current_app.config.get("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, secret, algorithms=[algo])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "View token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid view token"}), 401
    if payload.get("doc_id") != str(doc_id) or payload.get("view") != "pdf":
        return jsonify({"error": "Invalid token for this document"}), 403

    try:
        doc = document_find_by_id(doc_id)
    except Exception:
        return jsonify({"error": "Invalid document ID"}), 400
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    pdf_path = doc.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "PDF file not found"}), 404

    filename = doc.get("original_filename", "document.pdf")
    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename,
    )


@pdf_bp.route("/<doc_id>/stream", methods=["GET"])
def stream(doc_id):
    """Stream audio for in-browser playback (Range supported). No full download."""
    token = request.args.get("t")
    if not token:
        return jsonify({"error": "Missing stream token"}), 401
    secret = current_app.config["JWT_SECRET_KEY"]
    algo = current_app.config.get("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, secret, algorithms=[algo])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Stream token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid stream token"}), 401
    if payload.get("doc_id") != str(doc_id):
        return jsonify({"error": "Invalid token for this document"}), 403

    try:
        doc = document_find_by_id(doc_id)
    except Exception:
        return jsonify({"error": "Invalid document ID"}), 400
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    output_path = doc.get("output_path")
    if not output_path or not os.path.exists(output_path):
        return jsonify({"error": "Audio file not found"}), 404

    ext = os.path.splitext(output_path)[1].lower()
    mimetype = "audio/mpeg" if ext == ".mp3" else "audio/wav"
    return send_file(
        output_path,
        mimetype=mimetype,
        as_attachment=False,
        conditional=True,
    )

"""
Background worker for PDF processing.
"""
import os
import threading
from queue import Queue, Empty
from bson import ObjectId

from .models import document_update_status, document_find_by_id, get_documents_collection
from .services.pipeline_service import run_pipeline
from .config import Config


_task_queue: Queue = Queue()
_worker_started = False


def _get_pdf_name(pdf_path: str) -> str:
    return os.path.splitext(os.path.basename(pdf_path))[0]


def _get_output_audio_path(output_dir: str, pdf_path: str) -> str:
    name = _get_pdf_name(pdf_path)
    return os.path.join(output_dir, f"{name}.mp3")


def _worker_loop(app):
    """Worker thread: process pending documents."""
    with app.app_context():
        from flask import current_app
        while True:
            try:
                doc_id = _task_queue.get(timeout=5)
            except Empty:
                continue
            try:
                doc = document_find_by_id(doc_id)
                if not doc or doc["status"] != "pending":
                    continue
                pdf_path = doc.get("pdf_path")
                if not pdf_path or not os.path.exists(pdf_path):
                    document_update_status(doc_id, "failed", error_message="PDF file not found")
                    continue

                output_dir = os.path.join(
                    current_app.config["OUTPUTS_DIR"],
                    str(doc["user_id"]),
                    str(doc_id),
                )
                os.makedirs(output_dir, exist_ok=True)

                document_update_status(doc_id, "processing")

                success, err = run_pipeline(pdf_path, output_dir, doc_id=doc_id)
                if success:
                    audio_path = _get_output_audio_path(output_dir, pdf_path)
                    document_update_status(doc_id, "completed", output_path=audio_path)
                else:
                    document_update_status(doc_id, "failed", error_message=err or "Unknown error")
            except Exception as e:
                document_update_status(doc_id, "failed", error_message=str(e))
            finally:
                _task_queue.task_done()


def start_worker(app):
    """Start the background worker thread."""
    global _worker_started
    if _worker_started:
        return
    _worker_started = True
    t = threading.Thread(target=_worker_loop, args=(app,), daemon=True)
    t.start()


def enqueue_document(doc_id):
    """Add a document to the processing queue."""
    _task_queue.put(doc_id)

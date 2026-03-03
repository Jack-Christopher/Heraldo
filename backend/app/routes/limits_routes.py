"""
Public limits endpoint (no auth).
"""
from flask import Blueprint, jsonify, current_app

limits_bp = Blueprint("limits", __name__)


@limits_bp.route("/limits", methods=["GET"])
def get_limits():
    """Return public limits for the UI."""
    return jsonify({
        "max_pdfs_per_user": current_app.config.get("MAX_PDFS_PER_USER", 2),
        "max_words_per_pdf": current_app.config.get("MAX_WORDS_PER_PDF", 1500),
    })

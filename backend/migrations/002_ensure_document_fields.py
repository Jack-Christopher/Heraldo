"""
Data migration: ensure existing documents have required/optional fields.

Idempotent: update_many with $exists checks only touches docs that need updates.
"""


def migrate(db):
    # Ensure documents have progress cleared when completed/failed (legacy cleanup)
    db.documents.update_many(
        {"status": {"$in": ["completed", "failed"]}, "progress": {"$exists": True}},
        {"$unset": {"progress": ""}},
    )

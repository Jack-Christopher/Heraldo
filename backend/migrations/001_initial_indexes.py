"""
Initial indexes for users and documents collections.

Idempotent: create_index does nothing if index already exists.
"""
from pymongo import ASCENDING


def migrate(db):
    # Users: unique email
    db.users.create_index("email", unique=True)
    db.users.create_index("verification_token", sparse=True)

    # Documents: user listing, status counts
    db.documents.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
    db.documents.create_index([("user_id", ASCENDING), ("status", ASCENDING)])

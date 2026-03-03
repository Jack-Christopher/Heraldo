"""
Migrate username -> full_name for existing users.
"""


def migrate(db):
    for u in db.users.find({"username": {"$exists": True}, "full_name": {"$exists": False}}):
        db.users.update_one(
            {"_id": u["_id"]},
            {"$set": {"full_name": u["username"]}},
        )
    # Drop old username index if exists
    try:
        db.users.drop_index("username_1")
    except Exception:
        pass

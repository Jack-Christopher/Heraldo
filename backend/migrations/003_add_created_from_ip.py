"""
Add created_from_ip to existing users (for one-account-per-IP check).
"""


def migrate(db):
    for u in db.users.find({"created_from_ip": {"$exists": False}, "last_ip": {"$exists": True}}):
        db.users.update_one({"_id": u["_id"]}, {"$set": {"created_from_ip": u["last_ip"]}})
    db.users.create_index("created_from_ip")

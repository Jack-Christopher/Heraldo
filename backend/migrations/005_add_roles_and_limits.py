"""
Add role and per-user limits to users.
- role: "user" | "admin", default "user"
- limits: { max_pdfs_per_user, max_words_per_pdf } - optional overrides
"""


def migrate(db):
    # Add role to all users without it (default: user)
    result = db.users.update_many(
        {"role": {"$exists": False}},
        {"$set": {"role": "user"}},
    )
    # Add empty limits to users without it (use global config as fallback)
    db.users.update_many(
        {"limits": {"$exists": False}},
        {"$set": {"limits": {}}},
    )
    # Promote to admin by ADMIN_EMAILS env (comma-separated)
    import os
    admin_emails = [
        e.strip().lower()
        for e in (os.environ.get("ADMIN_EMAILS", "") or "").split(",")
        if e.strip()
    ]
    for email in admin_emails:
        db.users.update_many(
            {"email": {"$regex": f"^{email}$", "$options": "i"}},
            {"$set": {"role": "admin"}},
        )

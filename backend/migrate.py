#!/usr/bin/env python3
"""
Run MongoDB migrations.

Usage:
  python migrate.py
  python -m migrate

Can be run standalone (uses MONGODB_URI env) or via Flask app context.
"""
import os
import sys

# Add parent for PYTHONPATH when run as script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pymongo import MongoClient


def main():
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        print("MONGODB_URI not set", file=sys.stderr)
        sys.exit(1)

    client = MongoClient(uri)
    db = client.get_default_database()

    from migrations.runner import run_migrations
    run_migrations(db)
    print("Migrations complete")


if __name__ == "__main__":
    main()

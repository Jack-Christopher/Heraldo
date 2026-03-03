"""
Migration runner for MongoDB.

Tracks applied migrations in _migrations collection.
Runs only pending migrations (idempotent across deploys).
"""
from datetime import datetime
from pathlib import Path
import importlib.util
import sys


MIGRATIONS_COLLECTION = "_migrations"


def _get_migrations_dir() -> Path:
    return Path(__file__).resolve().parent


def _discover_migrations() -> list[tuple[str, Path]]:
    """Return sorted list of (name, path) for migration files."""
    migrations_dir = _get_migrations_dir()
    migrations = []
    for path in sorted(migrations_dir.iterdir()):
        if path.suffix == ".py" and path.name != "__init__.py" and path.name != "runner.py":
            if path.stem[0:4].isdigit():  # 001_*, 002_*, etc.
                migrations.append((path.stem, path))
    return migrations


def _load_migration_module(name: str, path: Path):
    """Load migration module by path."""
    spec = importlib.util.spec_from_file_location(f"migrations.{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load migration {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_migrations(db):
    """
    Run all pending migrations.
    Idempotent: only runs migrations not in _migrations collection.
    """
    coll = db[MIGRATIONS_COLLECTION]
    applied = {d["name"] for d in coll.find({}, {"name": 1})}

    for name, path in _discover_migrations():
        if name in applied:
            continue
        module = _load_migration_module(name, path)
        migrate_fn = getattr(module, "migrate", None)
        if not callable(migrate_fn):
            raise ValueError(f"Migration {name} has no migrate(db) function")
        migrate_fn(db)
        coll.insert_one({"name": name, "applied_at": datetime.utcnow()})

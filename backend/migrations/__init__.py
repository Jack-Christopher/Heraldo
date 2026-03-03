"""
MongoDB migrations for Heraldo.

Each migration file must expose:
  - name: str (e.g. "001_initial_indexes")
  - migrate(db) -> None
"""
from .runner import run_migrations

__all__ = ["run_migrations"]

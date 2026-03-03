"""
Configuration for Heraldo backend API.
"""
import os
from pathlib import Path

# Limits (business rules)
MAX_PDFS_PER_USER = 2
MAX_PAGES_PER_PDF = 5
MAX_WORDS_PER_PDF = 1500

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = os.environ.get("OUTPUTS_DIR", str(BASE_DIR / "outputs"))
UPLOADS_DIR = os.environ.get("UPLOADS_DIR", str(BASE_DIR / "uploads"))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.environ.get("JWT_SECRET") or "dev-secret-change-in-production"
    MONGODB_URI = os.environ.get("MONGODB_URI") or "mongodb://mongodb:27017/heraldo"
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET") or SECRET_KEY
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours
    OUTPUTS_DIR = OUTPUTS_DIR
    UPLOADS_DIR = UPLOADS_DIR
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB max upload
    MAX_PDFS_PER_USER = MAX_PDFS_PER_USER
    MAX_PAGES_PER_PDF = MAX_PAGES_PER_PDF
    MAX_WORDS_PER_PDF = MAX_WORDS_PER_PDF


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

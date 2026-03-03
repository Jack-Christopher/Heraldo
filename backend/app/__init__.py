"""
Heraldo Web API - Flask application factory.
"""
import os
from flask import Flask
from flask_cors import CORS

from .config import config_by_name


def create_app(config_name=None):
    """Create and configure the Flask application."""
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3001,http://127.0.0.1:3001").split(",")
    CORS(app, origins=[o.strip() for o in cors_origins if o.strip()])

    # Ensure directories exist
    os.makedirs(app.config["OUTPUTS_DIR"], exist_ok=True)
    os.makedirs(app.config["UPLOADS_DIR"], exist_ok=True)

    # Register blueprints
    from .routes.auth_routes import auth_bp
    from .routes.pdf_routes import pdf_bp
    from .routes.user_routes import user_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(pdf_bp, url_prefix="/api/pdf")
    app.register_blueprint(user_bp, url_prefix="/api/user")

    # Register limits endpoint (no auth)
    from .routes.limits_routes import limits_bp
    app.register_blueprint(limits_bp, url_prefix="/api")

    # Run MongoDB migrations (structure + data; idempotent, no-op on subsequent deploys)
    with app.app_context():
        try:
            from .models import get_db
            from migrations.runner import run_migrations
            run_migrations(get_db())
        except Exception:
            pass  # MongoDB may not be ready yet

    # Start background worker
    from .worker import start_worker
    start_worker(app)

    return app

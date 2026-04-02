"""Flask application factory."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    # Use absolute path for database
    db_path = Path(__file__).parent.parent / "instance" / "research.db"
    db_path.parent.mkdir(exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    from app import models
    with app.app_context():
        db.create_all()

    from app.auth import auth_bp
    from app.research import research_bp
    from app.export import export_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(research_bp)
    app.register_blueprint(export_bp)

    @app.route("/")
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            from flask import redirect
            return redirect("/dashboard")
        from flask import redirect
        return redirect("/login")

    @app.after_request
    def prevent_cache(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return app

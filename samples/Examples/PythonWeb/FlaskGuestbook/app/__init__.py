# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""FlaskGuestbook - Flask application factory.

create_app() builds the app: config class, the SQLite database helpers (app/db.py), the guestbook blueprint
(HTML pages) and the api blueprint (JSON).  `flask --app app init-db` creates an empty database.
"""
import os

from flask import Flask


def create_app(config_object="config.DevelopmentConfig"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.setdefault("DATABASE", os.path.join(app.instance_path, "guestbook.sqlite3"))

    from . import db
    db.init_app(app)

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    from .api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix="/api")
    return app

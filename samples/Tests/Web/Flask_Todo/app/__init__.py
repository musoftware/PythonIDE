"""Flask Todo - application factory."""
from flask import Flask


def create_app(config_object="config.DevelopmentConfig"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    from . import db
    db.init_app(app)

    from .todos import bp as todos_bp
    app.register_blueprint(todos_bp)
    from .api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    return app

from __future__ import annotations

from flask import Flask

from darwix_app.config import Config
from darwix_app.routes.api import api_bp
from darwix_app.routes.web import web_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    app.config["AUDIO_DIR"].mkdir(parents=True, exist_ok=True)
    app.config["IMAGE_DIR"].mkdir(parents=True, exist_ok=True)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app

import os
from flask import Flask
from .routes import bp

def create_app():
    app = Flask(__name__)
    ephe = os.environ.get("EPHE_PATH")
    if not ephe or not os.path.isdir(ephe):
        raise RuntimeError("EPHE_PATH not set or not a directory")
    app.config["EPHE_PATH"] = ephe

    # CORS (simple)
    from flask_cors import CORS
    origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    CORS(app, resources={r"/*": {"origins": origins}})

    app.register_blueprint(bp)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}, 200
    return app

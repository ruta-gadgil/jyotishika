import os
from flask import Flask
from .routes import bp

def create_app():
    app = Flask(__name__)
    ephe = os.environ.get("EPHE_PATH")
    if not ephe or not os.path.isdir(ephe):
        raise RuntimeError("EPHE_PATH not set or not a directory")
    app.config["EPHE_PATH"] = ephe

    # Ayanamsha configuration
    ayanamsha = os.environ.get("AYANAMSHA", "KRISHNAMURTI")
    allowed_ayanamsha = {"LAHIRI", "RAMAN", "KRISHNAMURTI", "VEDANJANAM"}
    if ayanamsha not in allowed_ayanamsha:
        raise RuntimeError(f"Invalid AYANAMSHA value: {ayanamsha}. Must be one of {allowed_ayanamsha}")
    app.config["AYANAMSHA"] = ayanamsha

    # CORS (simple)
    from flask_cors import CORS
    origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    CORS(app, resources={r"/*": {"origins": origins}})

    app.register_blueprint(bp)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}, 200
    return app

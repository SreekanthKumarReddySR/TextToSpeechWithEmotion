from __future__ import annotations

from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request, send_from_directory, session

from darwix_app.services.auth_service import AuthService
from darwix_app.services.empathy_engine import EmpathyEngine
from darwix_app.services.storyboard_service import StoryboardService
from darwix_app.services.tts_service import TextToSpeechService


api_bp = Blueprint("api", __name__)


def current_engine() -> EmpathyEngine:
    return EmpathyEngine(
        api_key=current_app.config["GEMINI_API_KEY"],
        model_name=current_app.config["GEMINI_MODEL"],
        output_dir=current_app.config["AUDIO_DIR"],
        enable_local_tts_fallback=current_app.config["ENABLE_LOCAL_TTS_FALLBACK"],
    )


def storyboard_service() -> StoryboardService:
    return StoryboardService(
        api_key=current_app.config["GEMINI_API_KEY"],
        model_name=current_app.config["GEMINI_MODEL"],
        image_model=current_app.config["GEMINI_IMAGE_MODEL"],
        output_dir=current_app.config["IMAGE_DIR"],
    )


def require_user():
    if not session.get("user"):
        return jsonify({"error": "Authentication required."}), 401
    return None


@api_bp.post("/auth/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    try:
        user = AuthService().signup(
            name=(payload.get("name") or "").strip(),
            email=(payload.get("email") or "").strip(),
            password=(payload.get("password") or "").strip(),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Signup failed due to a server error."}), 500

    session["user"] = user
    return jsonify({"user": user})


@api_bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    try:
        user = AuthService().login(
            email=(payload.get("email") or "").strip(),
            password=(payload.get("password") or "").strip(),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Login failed due to a server error."}), 500

    session["user"] = user
    return jsonify({"user": user})


@api_bp.get("/session")
def get_session():
    return jsonify({"user": session.get("user")})


@api_bp.get("/voices")
def list_voices():
    return jsonify({"voices": TextToSpeechService.list_voices()})


@api_bp.post("/challenge-1/synthesize")
def synthesize():
    unauthorized = require_user()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Text input is required."}), 400

    try:
        result = current_engine().synthesize(
            text=text,
            filename_root=uuid4().hex,
            voice_id=payload.get("voice_id"),
            gender=payload.get("gender"),
        )
        result["audio_url"] = f"/api/audio/{result['filename']}"
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"Speech generation failed: {exc}"}), 500


@api_bp.post("/challenge-2/storyboard")
def generate_storyboard():
    unauthorized = require_user()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    narrative = (payload.get("narrative") or "").strip()
    style = (payload.get("style") or "cinematic digital art").strip()
    if not narrative:
        return jsonify({"error": "Narrative input is required."}), 400

    try:
        result = storyboard_service().generate_storyboard(narrative=narrative, style=style)
        for panel in result["panels"]:
            panel["image_url"] = f"/api/storyboards/{panel['image_filename']}"
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"Storyboard generation failed: {exc}"}), 500


@api_bp.get("/audio/<path:filename>")
def serve_audio(filename: str):
    return send_from_directory(current_app.config["AUDIO_DIR"], filename)


@api_bp.get("/storyboards/<path:filename>")
def serve_storyboard(filename: str):
    return send_from_directory(current_app.config["IMAGE_DIR"], filename)

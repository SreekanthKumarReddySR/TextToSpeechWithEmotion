from __future__ import annotations

from flask import Blueprint, redirect, render_template, session, url_for


web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    if session.get("user"):
        return redirect(url_for("web.dashboard"))
    return render_template("auth.html")


@web_bp.get("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        return redirect(url_for("web.index"))
    return render_template("dashboard.html", user=user)


@web_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.index"))

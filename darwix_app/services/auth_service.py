from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from werkzeug.security import check_password_hash, generate_password_hash

from darwix_app.services.database import get_db


LOCAL_USERS: dict[str, dict[str, Any]] = {}


class AuthService:
    def signup(self, name: str, email: str, password: str) -> dict[str, Any]:
        if not name.strip():
            raise ValueError("Name is required.")

        email = email.strip().lower()
        if not email:
            raise ValueError("Email is required.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        user_doc = {
            "user_id": uuid4().hex,
            "name": name.strip(),
            "email": email,
            "password_hash": generate_password_hash(password),
            "created_at": datetime.now(timezone.utc),
        }

        db = get_db()
        if db is None:
            if email in LOCAL_USERS:
                raise ValueError("An account with this email already exists.")
            LOCAL_USERS[email] = user_doc
            return self._public_user(user_doc)

        existing = db.users.find_one({"email": email}, {"_id": 1})
        if existing:
            raise ValueError("An account with this email already exists.")

        db.users.insert_one(user_doc)
        return self._public_user(user_doc)

    def login(self, email: str, password: str) -> dict[str, Any]:
        email = email.strip().lower()
        if not email or not password:
            raise ValueError("Email and password are required.")
        db = get_db()

        if db is None:
            user_doc = LOCAL_USERS.get(email)
        else:
            user_doc = db.users.find_one({"email": email})

        if not user_doc or not check_password_hash(user_doc["password_hash"], password):
            raise ValueError("Invalid email or password.")

        return self._public_user(user_doc)

    @staticmethod
    def _public_user(user_doc: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": user_doc["user_id"],
            "name": user_doc["name"],
            "email": user_doc["email"],
        }

from __future__ import annotations

from functools import lru_cache

from flask import current_app
from pymongo import MongoClient
from pymongo.errors import PyMongoError


@lru_cache(maxsize=1)
def get_client(uri: str) -> MongoClient:
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def get_db():
    uri = current_app.config["MONGO_URI"]
    if not uri:
        return None

    try:
        client = get_client(uri)
        client.admin.command("ping")
        return client[current_app.config["MONGO_DB_NAME"]]
    except PyMongoError:
        return None

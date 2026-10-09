"""MongoDB client and collection access (users, transactions, budgets)."""
from __future__ import annotations

import logging
from functools import lru_cache

from django.conf import settings
from pymongo import ASCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

_indexes_ensured = False


class MongoConnectionError(Exception):
    """Raised when MongoDB is unavailable."""


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    uri = settings.MONGODB_URI
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        logger.exception("MongoDB connection failed")
        raise MongoConnectionError(
            "Unable to connect to MongoDB. Check MONGODB_URI and that the server is running."
        ) from exc


def get_db() -> Database:
    return get_client()[settings.MONGODB_DB_NAME]


def ensure_indexes() -> None:
    global _indexes_ensured
    if _indexes_ensured:
        return
    db = get_db()
    db.transactions.create_index(
        [("user_id", ASCENDING), ("transaction_date", ASCENDING)],
        name="user_id_transaction_date",
    )
    db.budgets.create_index(
        [("user_id", ASCENDING), ("year", ASCENDING), ("month", ASCENDING)],
        unique=True,
        name="user_id_year_month",
    )
    db.users.create_index([("email", ASCENDING)], unique=True, name="email_unique")
    _indexes_ensured = True


def transactions_collection():
    ensure_indexes()
    return get_db().transactions


def budgets_collection():
    ensure_indexes()
    return get_db().budgets

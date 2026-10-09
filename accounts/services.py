"""User accounts stored in MongoDB."""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from accounts.user import MongoUser
from expenses.mongo import ensure_indexes, get_db


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def users_collection():
    ensure_indexes()
    return get_db().users


def email_exists(email: str) -> bool:
    normalized = email.strip().lower()
    return users_collection().find_one({"email": normalized}, {"_id": 1}) is not None


def get_user_doc_by_email(email: str) -> dict | None:
    return users_collection().find_one({"email": email.strip().lower()})


def get_user_doc_by_id(user_id: str) -> dict | None:
    try:
        oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    return users_collection().find_one({"_id": oid})


def create_user(*, name: str, email: str, password: str) -> MongoUser:
    normalized_email = email.strip().lower()
    if email_exists(normalized_email):
        raise ValidationError({"email": ["An account with this email already exists."]})
    try:
        validate_password(password)
    except ValidationError:
        raise

    now = _utc_now()
    doc = {
        "email": normalized_email,
        "name": name.strip(),
        "password_hash": make_password(password),
        "created_at": now,
        "updated_at": now,
    }
    result = users_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return MongoUser(doc)


def authenticate_user(email: str, password: str) -> MongoUser | None:
    doc = get_user_doc_by_email(email)
    if not doc:
        return None
    user = MongoUser(doc)
    if user.check_password(password):
        return user
    return None


def get_user_by_id(user_id: str) -> MongoUser | None:
    doc = get_user_doc_by_id(user_id)
    if not doc:
        return None
    return MongoUser(doc)

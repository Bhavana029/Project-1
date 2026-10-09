"""Non-ORM user object for Django auth integration (data lives in MongoDB)."""
from __future__ import annotations

from django.contrib.auth.hashers import check_password


class _MongoUserMeta:
    """Lets django.contrib.auth.login store the user id in the session."""

    class _Pk:
        @staticmethod
        def value_to_string(user) -> str:
            return str(user.pk)

    pk = _Pk()


class MongoUser:
    """Minimal user interface compatible with Django templates and login_required."""

    _meta = _MongoUserMeta()

    def __init__(self, doc: dict):
        self._doc = doc
        self.pk = str(doc["_id"])
        self.id = self.pk
        self.email = doc["email"]
        self.username = doc["email"]
        self.first_name = doc.get("name", "")
        self.is_active = True
        self.is_staff = False
        self.is_superuser = False

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self._doc["password_hash"])

    def get_username(self) -> str:
        return self.email

    def save(self, *args, **kwargs):
        """No-op: required so Django's user_logged_in signal does not crash."""

    def __str__(self) -> str:
        return self.email


"""Non-ORM user object for Django authentication."""

from django.contrib.auth.hashers import check_password


class MongoUser:
    """Custom user object backed by MongoDB."""

    def __init__(self, doc):
        self._doc = doc
        self.pk = str(doc["_id"])
        self.id = self.pk
        self.email = doc["email"]
        self.username = doc["email"]
        self.first_name = doc.get("name", "")
        self.is_active = True
        self.is_staff = False
        self.is_superuser = False
        self.backend = "accounts.backends.MongoDBBackend"

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def check_password(self, raw_password):
        return check_password(
            raw_password,
            self._doc["password_hash"],
        )

    def get_username(self):
        return self.email

    def save(self, *args, **kwargs):
        """Compatibility method for Django login signals."""

    def __str__(self):
        return self.email

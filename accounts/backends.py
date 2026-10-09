
from accounts.services import authenticate_user, get_user_by_id


class MongoDBBackend:
    """Authenticate against MongoDB users collection."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email") or username

        if not email or not password:
            return None

        return authenticate_user(email, password)

    def get_user(self, user_id):
        print("MongoDBBackend.get_user called with:", repr(user_id), type(user_id))

        if not isinstance(user_id, str):
            user_id = str(user_id)

        return get_user_by_id(user_id)



"""Authentication middleware compatible with MongoDB-backed users."""

from django.contrib.auth import get_user
from django.contrib.auth.middleware import AuthenticationMiddleware


def get_mongo_user(request):
    """Restore the user through the configured MongoDB backend."""
    user_id = request.session.get("_auth_user_id")
    backend_path = request.session.get("_auth_user_backend")

    if not user_id or backend_path != "accounts.backends.MongoDBBackend":
        return get_user(request)

    from accounts.services import get_user_by_id

    return get_user_by_id(str(user_id))


class MongoAuthenticationMiddleware(AuthenticationMiddleware):
    def process_request(self, request):
        request.user = get_mongo_user(request)

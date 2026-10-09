from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.test import Client, TestCase
from django.urls import reverse

from accounts.services import create_user, email_exists, get_user_by_id


class InMemoryUsersCollection:
    """Test double for MongoDB users collection."""

    def __init__(self):
        self.by_email: dict[str, dict] = {}
        self.by_id: dict[str, dict] = {}

    def create_index(self, *args, **kwargs):
        return None

    def insert_one(self, doc):
        oid = ObjectId()
        stored = {**doc, "_id": oid}
        self.by_email[stored["email"]] = stored
        self.by_id[str(oid)] = stored
        result = MagicMock()
        result.inserted_id = oid
        return result

    def find_one(self, query, *args, **kwargs):
        if "email" in query:
            return self.by_email.get(query["email"])
        if "_id" in query:
            return self.by_id.get(str(query["_id"]))
        return None


@patch("accounts.services.users_collection")
class RegistrationLoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.store = InMemoryUsersCollection()

    def _bind_store(self, mock_coll):
        mock_coll.return_value = self.store

    def test_register_and_login_flow(self, mock_coll):
        self._bind_store(mock_coll)
        reg_url = reverse("accounts:register")
        response = self.client.post(
            reg_url,
            {
                "name": "Test User",
                "email": "test@example.com",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
            },
        )
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        self.assertTrue(email_exists("test@example.com"))

        self.client.logout()
        login_url = reverse("accounts:login")
        bad = self.client.post(
            login_url,
            {"email": "test@example.com", "password": "wrong"},
        )
        self.assertEqual(bad.status_code, 200)
        self.assertFormError(bad.context["form"], None, "Invalid email or password.")

        good = self.client.post(
            login_url,
            {"email": "test@example.com", "password": "StrongPass123!"},
        )
        self.assertRedirects(good, reverse("dashboard"), fetch_redirect_response=False)

    def test_duplicate_email_rejected(self, mock_coll):
        self._bind_store(mock_coll)
        create_user(name="First", email="dup@example.com", password="StrongPass123!")
        response = self.client.post(
            reverse("accounts:register"),
            {
                "name": "Another",
                "email": "dup@example.com",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "An account with this email already exists.",
        )

    def test_protected_dashboard_requires_login(self, mock_coll):
        self._bind_store(mock_coll)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next=/dashboard/")


@patch("accounts.services.users_collection")
class MongoUserServiceTests(TestCase):
    def test_get_user_by_id(self, mock_coll):
        store = InMemoryUsersCollection()
        mock_coll.return_value = store
        user = create_user(name="A", email="a@example.com", password="StrongPass123!")
        loaded = get_user_by_id(user.pk)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.email, "a@example.com")

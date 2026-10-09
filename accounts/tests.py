from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class RegistrationLoginTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_and_login_flow(self):
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
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(User.objects.filter(email="test@example.com").exists())

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
        self.assertRedirects(good, reverse("dashboard"))

    def test_duplicate_email_rejected(self):
        User.objects.create_user(
            username="dup@example.com",
            email="dup@example.com",
            password="StrongPass123!",
        )
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

    def test_protected_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next=/dashboard/")

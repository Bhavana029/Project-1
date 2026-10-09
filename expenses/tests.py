from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from expenses.money_utils import decimal_from_input, from_stored
from expenses.services import create_transaction, delete_transaction, get_transaction_for_user

User = get_user_model()


class MoneyUtilsTests(TestCase):
    def test_decimal_from_input_rejects_zero(self):
        with self.assertRaises(ValueError):
            decimal_from_input("0")

    def test_from_stored_decimal128(self):
        from bson.decimal128 import Decimal128

        value = from_stored(Decimal128("10.50"))
        self.assertEqual(value, Decimal("10.50"))


class TransactionSecurityTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username="a@example.com", email="a@example.com", password="StrongPass123!"
        )
        self.user_b = User.objects.create_user(
            username="b@example.com", email="b@example.com", password="StrongPass123!"
        )
        self.client = Client()

    @patch("expenses.services.transactions_collection")
    def test_user_cannot_access_other_users_transaction(self, mock_coll):
        mock_coll.return_value.find_one.return_value = None
        tx = get_transaction_for_user(self.user_b, "507f1f77bcf86cd799439011")
        self.assertIsNone(tx)
        query = mock_coll.return_value.find_one.call_args[0][0]
        self.assertEqual(query["user_id"], str(self.user_b.pk))

    @patch("expenses.services.transactions_collection")
    def test_create_transaction_calls_insert(self, mock_coll):
        inserted_id = MagicMock()
        mock_coll.return_value.insert_one.return_value.inserted_id = inserted_id
        user = self.user_a
        result = create_transaction(
            user,
            title="Groceries",
            amount=Decimal("850.00"),
            transaction_type="expense",
            category="Food",
            transaction_date=date(2026, 10, 9),
        )
        self.assertEqual(result["title"], "Groceries")
        mock_coll.return_value.insert_one.assert_called_once()

    @patch("expenses.services.transactions_collection")
    def test_delete_requires_ownership(self, mock_coll):
        mock_coll.return_value.delete_one.return_value.deleted_count = 0
        self.assertFalse(delete_transaction(self.user_b, "507f1f77bcf86cd799439011"))

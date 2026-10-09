"""Monthly budget records in MongoDB."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from pymongo import ReturnDocument

from expenses.money_utils import from_stored, to_decimal128
from expenses.mongo import budgets_collection
from expenses.services import month_expense_total


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _user_id(user) -> str:
    return str(user.pk)


def get_budget(user, year: int, month: int) -> dict | None:
    doc = budgets_collection().find_one(
        {"user_id": _user_id(user), "year": year, "month": month}
    )
    if not doc:
        return None
    limit = from_stored(doc.get("monthly_limit"))
    return {
        "id": str(doc["_id"]),
        "year": doc["year"],
        "month": doc["month"],
        "monthly_limit": limit,
    }


def set_budget(user, year: int, month: int, monthly_limit: Decimal) -> dict:
    if monthly_limit <= 0:
        raise ValueError("Budget must be greater than zero.")
    now = _utc_now()
    doc = budgets_collection().find_one_and_update(
        {"user_id": _user_id(user), "year": year, "month": month},
        {
            "$set": {
                "monthly_limit": to_decimal128(monthly_limit),
                "updated_at": now,
            },
            "$setOnInsert": {
                "user_id": _user_id(user),
                "year": year,
                "month": month,
                "created_at": now,
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    limit = from_stored(doc.get("monthly_limit"))
    return {"year": year, "month": month, "monthly_limit": limit}


def budget_status(user, year: int | None = None, month: int | None = None) -> dict:
    today = date.today()
    year = year or today.year
    month = month or today.month
    budget = get_budget(user, year, month)
    spent = month_expense_total(user, year, month)
    limit = budget["monthly_limit"] if budget else None
    remaining = None
    percent = None
    warning_level = "none"
    if limit is not None and limit > 0:
        remaining = limit - spent
        percent = float((spent / limit) * 100)
        if percent >= 100:
            warning_level = "danger"
        elif percent >= 80:
            warning_level = "warning"
    return {
        "year": year,
        "month": month,
        "monthly_limit": limit,
        "spent": spent,
        "remaining": remaining,
        "percent": percent,
        "warning_level": warning_level,
        "has_budget": limit is not None,
    }

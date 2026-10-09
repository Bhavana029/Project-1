"""Business logic for transactions stored in MongoDB."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from pymongo import ReturnDocument

from expenses.categories import ALL_CATEGORIES, TRANSACTION_TYPES, categories_for_type
from expenses.money_utils import format_money, from_stored, to_decimal128
from expenses.mongo import transactions_collection


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _user_id(user) -> str:
    return str(user.pk)


def is_valid_object_id(value: str) -> bool:
    try:
        ObjectId(value)
        return True
    except (InvalidId, TypeError):
        return False


def _doc_to_dict(doc: dict) -> dict:
    amount = from_stored(doc.get("amount"))
    return {
        "id": str(doc["_id"]),
        "user_id": doc["user_id"],
        "title": doc["title"],
        "amount": amount,
        "amount_display": format_money(amount),
        "type": doc["type"],
        "category": doc["category"],
        "transaction_date": doc["transaction_date"],
        "payment_method": doc.get("payment_method") or "",
        "notes": doc.get("notes") or "",
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def _validate_transaction_fields(
    *,
    title: str,
    amount: Decimal,
    transaction_type: str,
    category: str,
    transaction_date: date,
) -> None:
    if not title or not title.strip():
        raise ValueError("Title is required.")
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError("Invalid transaction type.")
    allowed = categories_for_type(transaction_type)
    if category not in allowed:
        raise ValueError("Invalid category for this transaction type.")
    if transaction_date > date.today():
        raise ValueError("Transaction date cannot be in the future.")


def create_transaction(
    user,
    *,
    title: str,
    amount: Decimal,
    transaction_type: str,
    category: str,
    transaction_date: date,
    payment_method: str = "",
    notes: str = "",
) -> dict:
    _validate_transaction_fields(
        title=title,
        amount=amount,
        transaction_type=transaction_type,
        category=category,
        transaction_date=transaction_date,
    )
    now = _utc_now()
    doc = {
        "user_id": _user_id(user),
        "title": title.strip(),
        "amount": to_decimal128(amount),
        "type": transaction_type,
        "category": category,
        "transaction_date": transaction_date.isoformat(),
        "payment_method": payment_method.strip() if payment_method else "",
        "notes": notes.strip() if notes else "",
        "created_at": now,
        "updated_at": now,
    }
    result = transactions_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _doc_to_dict(doc)


def get_transaction_for_user(user, transaction_id: str) -> dict | None:
    if not is_valid_object_id(transaction_id):
        return None
    doc = transactions_collection().find_one(
        {"_id": ObjectId(transaction_id), "user_id": _user_id(user)}
    )
    if not doc:
        return None
    return _doc_to_dict(doc)


def update_transaction(
    user,
    transaction_id: str,
    *,
    title: str,
    amount: Decimal,
    transaction_type: str,
    category: str,
    transaction_date: date,
    payment_method: str = "",
    notes: str = "",
) -> dict | None:
    if not is_valid_object_id(transaction_id):
        return None
    _validate_transaction_fields(
        title=title,
        amount=amount,
        transaction_type=transaction_type,
        category=category,
        transaction_date=transaction_date,
    )
    update = {
        "$set": {
            "title": title.strip(),
            "amount": to_decimal128(amount),
            "type": transaction_type,
            "category": category,
            "transaction_date": transaction_date.isoformat(),
            "payment_method": payment_method.strip() if payment_method else "",
            "notes": notes.strip() if notes else "",
            "updated_at": _utc_now(),
        }
    }
    doc = transactions_collection().find_one_and_update(
        {"_id": ObjectId(transaction_id), "user_id": _user_id(user)},
        update,
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        return None
    return _doc_to_dict(doc)


def delete_transaction(user, transaction_id: str) -> bool:
    if not is_valid_object_id(transaction_id):
        return False
    result = transactions_collection().delete_one(
        {"_id": ObjectId(transaction_id), "user_id": _user_id(user)}
    )
    return result.deleted_count == 1


def _build_filter_query(
    user,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    transaction_type: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {"user_id": _user_id(user)}
    if transaction_type and transaction_type in TRANSACTION_TYPES:
        query["type"] = transaction_type
    if category and category in ALL_CATEGORIES:
        query["category"] = category
    if date_from or date_to:
        date_filter: dict[str, str] = {}
        if date_from:
            date_filter["$gte"] = date_from.isoformat()
        if date_to:
            date_filter["$lte"] = date_to.isoformat()
        query["transaction_date"] = date_filter
    if search and search.strip():
        pattern = search.strip()
        query["$or"] = [
            {"title": {"$regex": pattern, "$options": "i"}},
            {"notes": {"$regex": pattern, "$options": "i"}},
        ]
    return query


def list_transactions(
    user,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    transaction_type: str | None = None,
    search: str | None = None,
    sort: str = "date_desc",
    page: int = 1,
    page_size: int = 10,
) -> dict:
    query = _build_filter_query(
        user,
        date_from=date_from,
        date_to=date_to,
        category=category,
        transaction_type=transaction_type,
        search=search,
    )
    sort_key = "transaction_date"
    direction = -1
    if sort == "date_asc":
        direction = 1
    elif sort == "amount_desc":
        sort_key = "amount"
        direction = -1
    elif sort == "amount_asc":
        sort_key = "amount"
        direction = 1

    coll = transactions_collection()
    total = coll.count_documents(query)
    paginator = Paginator(range(total), page_size)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)
    skip = (page_obj.number - 1) * page_size
    cursor = coll.find(query).sort(sort_key, direction).skip(skip).limit(page_size)
    items = [_doc_to_dict(d) for d in cursor]
    page_obj.object_list = items
    return {
        "page_obj": page_obj,
        "paginator": paginator,
        "items": items,
    }


def transactions_for_export(
    user,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    transaction_type: str | None = None,
    search: str | None = None,
    sort: str = "date_desc",
) -> list[dict]:
    result = list_transactions(
        user,
        date_from=date_from,
        date_to=date_to,
        category=category,
        transaction_type=transaction_type,
        search=search,
        sort=sort,
        page=1,
        page_size=100000,
    )
    return result["items"]


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    from datetime import timedelta

    last_day = end - timedelta(days=1)
    return start.isoformat(), last_day.isoformat()


def sum_by_type(user, transaction_type: str, date_from: str | None = None, date_to: str | None = None) -> Decimal:
    query: dict[str, Any] = {"user_id": _user_id(user), "type": transaction_type}
    if date_from or date_to:
        df: dict[str, str] = {}
        if date_from:
            df["$gte"] = date_from
        if date_to:
            df["$lte"] = date_to
        query["transaction_date"] = df
    total = Decimal("0.00")
    for doc in transactions_collection().find(query):
        total += from_stored(doc.get("amount"))
    return total


def dashboard_summary(user, year: int | None = None, month: int | None = None) -> dict:
    today = date.today()
    year = year or today.year
    month = month or today.month
    month_start, month_end = _month_bounds(year, month)

    total_income = sum_by_type(user, "income")
    total_expense = sum_by_type(user, "expense")
    month_expense = sum_by_type(user, "expense", month_start, month_end)
    balance = total_income - total_expense

    recent = list_transactions(user, page=1, page_size=5)["items"]

    return {
        "total_income": total_income,
        "total_expenses": total_expense,
        "balance": balance,
        "month_expenses": month_expense,
        "recent_transactions": recent,
        "year": year,
        "month": month,
    }


def expense_by_category(user, year: int, month: int) -> list[dict]:
    month_start, month_end = _month_bounds(year, month)
    query = {
        "user_id": _user_id(user),
        "type": "expense",
        "transaction_date": {"$gte": month_start, "$lte": month_end},
    }
    totals: dict[str, Decimal] = {}
    for doc in transactions_collection().find(query):
        cat = doc.get("category", "Other")
        totals[cat] = totals.get(cat, Decimal("0.00")) + from_stored(doc.get("amount"))
    return [{"category": k, "total": v, "total_display": format_money(v)} for k, v in sorted(totals.items())]


def daily_expense_trend(user, year: int, month: int) -> list[dict]:
    month_start, month_end = _month_bounds(year, month)
    query = {
        "user_id": _user_id(user),
        "type": "expense",
        "transaction_date": {"$gte": month_start, "$lte": month_end},
    }
    totals: dict[str, Decimal] = {}
    for doc in transactions_collection().find(query):
        day = doc.get("transaction_date", "")
        totals[day] = totals.get(day, Decimal("0.00")) + from_stored(doc.get("amount"))
    return [{"date": k, "total": float(v)} for k, v in sorted(totals.items())]


def monthly_report(user, year: int, month: int) -> dict:
    month_start, month_end = _month_bounds(year, month)
    income = sum_by_type(user, "income", month_start, month_end)
    expenses = sum_by_type(user, "expense", month_start, month_end)
    by_category = expense_by_category(user, year, month)
    return {
        "year": year,
        "month": month,
        "income": income,
        "expenses": expenses,
        "net": income - expenses,
        "by_category": by_category,
    }


def month_expense_total(user, year: int, month: int) -> Decimal:
    month_start, month_end = _month_bounds(year, month)
    return sum_by_type(user, "expense", month_start, month_end)

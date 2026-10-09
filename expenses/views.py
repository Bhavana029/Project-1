import csv
import json
from datetime import date
from io import StringIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from budgets.services import budget_status
from expenses.categories import EXPENSE_CATEGORIES, INCOME_CATEGORIES
from expenses.forms import TransactionFilterForm, TransactionForm
from expenses.money_utils import format_money
from expenses.mongo import MongoConnectionError
from expenses.services import (
    create_transaction,
    daily_expense_trend,
    dashboard_summary,
    delete_transaction,
    expense_by_category,
    get_transaction_for_user,
    list_transactions,
    monthly_report,
    transactions_for_export,
    update_transaction,
)


def _transaction_form_context(form, page_title: str, transaction=None) -> dict:
    return {
        "form": form,
        "page_title": page_title,
        "transaction": transaction,
        "income_categories_json": json.dumps(INCOME_CATEGORIES),
        "expense_categories_json": json.dumps(EXPENSE_CATEGORIES),
    }


def _handle_mongo(view_func):
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except MongoConnectionError:
            messages.error(
                request,
                "Database temporarily unavailable. Please check MongoDB and try again.",
            )
            return render(request, "error_db.html", status=503)

    return wrapper


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("accounts:login")


@login_required
@require_GET
@_handle_mongo
def dashboard_view(request):
    summary = dashboard_summary(request.user)
    categories = expense_by_category(request.user, summary["year"], summary["month"])
    trend = daily_expense_trend(request.user, summary["year"], summary["month"])
    budget = budget_status(request.user, summary["year"], summary["month"])

    chart_labels = [t["date"] for t in trend]
    chart_values = [t["total"] for t in trend]
    cat_labels = [c["category"] for c in categories]
    cat_values = [float(c["total"]) for c in categories]

    context = {
        "summary": summary,
        "summary_display": {
            "total_income": format_money(summary["total_income"]),
            "total_expenses": format_money(summary["total_expenses"]),
            "balance": format_money(summary["balance"]),
            "month_expenses": format_money(summary["month_expenses"]),
        },
        "recent_transactions": summary["recent_transactions"],
        "budget": budget,
        "budget_display": {
            "spent": format_money(budget["spent"]),
            "remaining": format_money(budget["remaining"]) if budget["remaining"] is not None else None,
            "monthly_limit": format_money(budget["monthly_limit"]) if budget["monthly_limit"] else None,
        },
        "chart_labels_json": json.dumps(chart_labels),
        "chart_values_json": json.dumps(chart_values),
        "cat_labels_json": json.dumps(cat_labels),
        "cat_values_json": json.dumps(cat_values),
    }
    return render(request, "dashboard.html", context)


@login_required
@require_http_methods(["GET", "POST"])
@_handle_mongo
def transaction_add(request):
    form = TransactionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        create_transaction(
            request.user,
            title=form.cleaned_data["title"],
            amount=form.cleaned_data["amount"],
            transaction_type=form.cleaned_data["type"],
            category=form.cleaned_data["category"],
            transaction_date=form.cleaned_data["transaction_date"],
            payment_method=form.cleaned_data.get("payment_method") or "",
            notes=form.cleaned_data.get("notes") or "",
        )
        messages.success(request, "Transaction added successfully.")
        return redirect("expenses:transaction_list")
    return render(
        request,
        "expenses/transaction_form.html",
        _transaction_form_context(form, "Add Transaction"),
    )


@login_required
@require_GET
@_handle_mongo
def transaction_list(request):
    filter_form = TransactionFilterForm(request.GET or None)
    params = {}
    if filter_form.is_valid():
        params = filter_form.cleaned_data
    else:
        params = {"sort": "date_desc"}

    result = list_transactions(
        request.user,
        date_from=params.get("date_from"),
        date_to=params.get("date_to"),
        category=params.get("category") or None,
        transaction_type=params.get("type") or None,
        search=params.get("q"),
        sort=params.get("sort") or "date_desc",
        page=int(request.GET.get("page", 1)),
        page_size=settings.TRANSACTIONS_PAGE_SIZE,
    )
    query = request.GET.copy()
    query.pop("page", None)
    pagination_query = query.urlencode()
    return render(
        request,
        "expenses/transaction_list.html",
        {
            "filter_form": filter_form,
            "page_obj": result["page_obj"],
            "transactions": result["items"],
            "pagination_query": pagination_query,
            "has_filters": any(
                request.GET.get(k)
                for k in ("q", "type", "category", "date_from", "date_to")
            ),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
@_handle_mongo
def transaction_edit(request, transaction_id):
    tx = get_transaction_for_user(request.user, transaction_id)
    if not tx:
        raise Http404("Transaction not found.")
    initial = {
        "title": tx["title"],
        "amount": tx["amount"],
        "type": tx["type"],
        "category": tx["category"],
        "transaction_date": date.fromisoformat(tx["transaction_date"]),
        "payment_method": tx["payment_method"],
        "notes": tx["notes"],
    }
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            updated = update_transaction(
                request.user,
                transaction_id,
                title=form.cleaned_data["title"],
                amount=form.cleaned_data["amount"],
                transaction_type=form.cleaned_data["type"],
                category=form.cleaned_data["category"],
                transaction_date=form.cleaned_data["transaction_date"],
                payment_method=form.cleaned_data.get("payment_method") or "",
                notes=form.cleaned_data.get("notes") or "",
            )
            if updated:
                messages.success(request, "Transaction updated.")
                return redirect("expenses:transaction_list")
            raise Http404("Transaction not found.")
    else:
        form = TransactionForm(initial=initial)
    return render(
        request,
        "expenses/transaction_form.html",
        _transaction_form_context(form, "Edit Transaction", transaction=tx),
    )


@login_required
@require_POST
@_handle_mongo
def transaction_delete(request, transaction_id):
    if delete_transaction(request.user, transaction_id):
        messages.success(request, "Transaction deleted.")
    else:
        messages.error(request, "Could not delete transaction.")
    return redirect("expenses:transaction_list")


def _parse_month_params(request) -> tuple[int, int]:
    today = date.today()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        if not (1 <= month <= 12):
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month
    return year, month


@login_required
@require_GET
@_handle_mongo
def reports_view(request):
    year, month = _parse_month_params(request)
    report = monthly_report(request.user, year, month)
    report_display = {
        "income": format_money(report["income"]),
        "expenses": format_money(report["expenses"]),
        "net": format_money(report["net"]),
    }
    cat_labels = [c["category"] for c in report["by_category"]]
    cat_values = [float(c["total"]) for c in report["by_category"]]
    return render(
        request,
        "reports.html",
        {
            "report": report,
            "report_display": report_display,
            "year": year,
            "month": month,
            "cat_labels_json": json.dumps(cat_labels),
            "cat_values_json": json.dumps(cat_values),
        },
    )


@login_required
@require_GET
@_handle_mongo
def reports_export_csv(request):
    filter_form = TransactionFilterForm(request.GET or None)
    params = filter_form.cleaned_data if filter_form.is_valid() else {"sort": "date_desc"}
    year, month = _parse_month_params(request)
    items = transactions_for_export(
        request.user,
        date_from=params.get("date_from"),
        date_to=params.get("date_to"),
        category=params.get("category") or None,
        transaction_type=params.get("type") or None,
        search=params.get("q"),
        sort=params.get("sort") or "date_desc",
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Date", "Title", "Type", "Category", "Amount", "Payment Method", "Notes"]
    )
    for tx in items:
        writer.writerow(
            [
                tx["transaction_date"],
                tx["title"],
                tx["type"],
                tx["category"],
                tx["amount_display"],
                tx["payment_method"],
                tx["notes"],
            ]
        )
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="transactions_{year}_{month}.csv"'
    return response

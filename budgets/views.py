from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from budgets.forms import BudgetForm
from budgets.services import budget_status, set_budget
from expenses.money_utils import format_money
from expenses.views import _handle_mongo


@login_required
@require_http_methods(["GET", "POST"])
@_handle_mongo
def budget_view(request):
    today = date.today()
    source = request.POST if request.method == "POST" else request.GET
    try:
        year = int(source.get("year", today.year))
        month = int(source.get("month", today.month))
        if not (1 <= month <= 12):
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month

    status = budget_status(request.user, year, month)
    initial = {}
    if status.get("monthly_limit"):
        initial["monthly_limit"] = status["monthly_limit"]
    form = BudgetForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        set_budget(request.user, year, month, form.cleaned_data["monthly_limit"])
        messages.success(request, "Budget saved.")
        return redirect(f"{request.path}?year={year}&month={month}")

    display = {
        "spent": format_money(status["spent"]),
        "remaining": format_money(status["remaining"]) if status["remaining"] is not None else "—",
        "monthly_limit": format_money(status["monthly_limit"]) if status["monthly_limit"] else "—",
    }
    return render(
        request,
        "budgets/budget.html",
        {"form": form, "status": status, "display": display, "year": year, "month": month},
    )

from django.urls import include, path

from config.health import health_check
from expenses.views import dashboard_view, home_redirect, reports_export_csv, reports_view

urlpatterns = [
    path("health/", health_check, name="health"),
    path("", home_redirect, name="home"),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("transactions/", include("expenses.urls")),
    path("budget/", include("budgets.urls")),
    path("reports/", reports_view, name="reports"),
    path("reports/export.csv", reports_export_csv, name="reports_export_csv"),
]

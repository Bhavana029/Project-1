from django.urls import path

from budgets import views

app_name = "budgets"

urlpatterns = [
    path("", views.budget_view, name="budget"),
]

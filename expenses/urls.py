from django.urls import path

from expenses import views

app_name = "expenses"

urlpatterns = [
    path("", views.transaction_list, name="transaction_list"),
    path("add/", views.transaction_add, name="transaction_add"),
    path("<str:transaction_id>/edit/", views.transaction_edit, name="transaction_edit"),
    path("<str:transaction_id>/delete/", views.transaction_delete, name="transaction_delete"),
]

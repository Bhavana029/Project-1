from datetime import date

from django import forms

from expenses.categories import (
    ALL_CATEGORIES,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    PAYMENT_METHODS,
    TRANSACTION_TYPES,
    categories_for_type,
)
from expenses.money_utils import decimal_from_input


class TransactionForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Groceries", "autocomplete": "off"}),
    )
    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01", "min": "0.01"}),
    )
    type = forms.ChoiceField(
        choices=[("expense", "Expense"), ("income", "Income")],
        widget=forms.Select(attrs={"id": "id_type"}),
    )
    category = forms.ChoiceField(choices=[(c, c) for c in EXPENSE_CATEGORIES])
    transaction_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date.today,
    )
    payment_method = forms.ChoiceField(choices=PAYMENT_METHODS, required=False)
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Optional notes"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tx_type = self.data.get("type") or self.initial.get("type") or "expense"
        cats = categories_for_type(tx_type)
        self.fields["category"].choices = [(c, c) for c in cats]

    def clean_amount(self):
        value = self.cleaned_data["amount"]
        try:
            return decimal_from_input(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def clean_transaction_date(self):
        value = self.cleaned_data["transaction_date"]
        if value > date.today():
            raise forms.ValidationError("Transaction date cannot be in the future.")
        return value

    def clean(self):
        cleaned = super().clean()
        tx_type = cleaned.get("type")
        category = cleaned.get("category")
        if tx_type and category:
            allowed = categories_for_type(tx_type)
            if category not in allowed:
                raise forms.ValidationError({"category": "Invalid category for this type."})
        return cleaned


class TransactionFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search")
    type = forms.ChoiceField(
        required=False,
        choices=[("", "All types"), ("expense", "Expense"), ("income", "Income")],
    )
    category = forms.ChoiceField(
        required=False,
        choices=[("", "All categories")] + [(c, c) for c in ALL_CATEGORIES],
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ("date_desc", "Newest first"),
            ("date_asc", "Oldest first"),
            ("amount_desc", "Amount high to low"),
            ("amount_asc", "Amount low to high"),
        ],
        initial="date_desc",
    )

from django import forms

from expenses.money_utils import decimal_from_input


class BudgetForm(forms.Form):
    monthly_limit = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        label="Monthly expense budget",
        widget=forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01", "min": "0.01"}),
    )

    def clean_monthly_limit(self):
        value = self.cleaned_data["monthly_limit"]
        try:
            return decimal_from_input(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc

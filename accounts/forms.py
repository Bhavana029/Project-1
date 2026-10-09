from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from accounts.services import email_exists
from expenses.mongo import MongoConnectionError


class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=150, label="Full name")
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        try:
            if email_exists(email):
                raise ValidationError("An account with this email already exists.")
        except MongoConnectionError as exc:
            raise ValidationError(
                "Unable to verify email right now. Please try again."
            ) from exc
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if password and confirm and password != confirm:
            raise ValidationError({"confirm_password": "Passwords do not match."})
        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                raise ValidationError({"password": exc.messages}) from exc
        return cleaned


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

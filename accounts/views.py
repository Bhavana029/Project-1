from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.forms import LoginForm, RegistrationForm
from accounts.services import create_user
from expenses.mongo import MongoConnectionError


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = create_user(
                name=form.cleaned_data["name"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
        except MongoConnectionError:
            messages.error(
                request,
                "Database temporarily unavailable. Please try again later.",
            )
            return render(request, "accounts/register.html", {"form": form}, status=503)
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errs in exc.message_dict.items():
                    form.add_error(field if field != "__all__" else None, errs)
            else:
                form.add_error(None, exc.messages if hasattr(exc, "messages") else str(exc))
            return render(request, "accounts/register.html", {"form": form})
        login(request, user, backend="accounts.backends.MongoDBBackend")
        messages.success(request, "Welcome! Your account has been created.")
        return redirect("dashboard")
    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        password = form.cleaned_data["password"]
        try:
            auth_user = authenticate(
                request,
                email=email,
                password=password,
                backend="accounts.backends.MongoDBBackend",
            )
        except MongoConnectionError:
            messages.error(
                request,
                "Database temporarily unavailable. Please try again later.",
            )
            return render(request, "accounts/login.html", {"form": form}, status=503)
        if auth_user is not None:
            login(request, auth_user, backend="accounts.backends.MongoDBBackend")
            return redirect("dashboard")
        form.add_error(None, "Invalid email or password.")
    return render(request, "accounts/login.html", {"form": form})


@login_required
@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("accounts:login")

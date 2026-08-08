from allauth.socialaccount.adapter import get_adapter as get_social_adapter
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.models import CustomUser


LOGIN_TEMPLATE = "core/auth/login.html"


def _destination_for(user):
    return "admin_dashboard" if user.is_platform_admin else "workspace_home"


def _password_login_redirect():
    return redirect(f"{reverse('login')}?method=password")


def login_view(request):
    if request.user.is_authenticated and request.user.is_authorized_user:
        return redirect(_destination_for(request.user))

    if request.user.is_authenticated:
        logout(request)

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return _password_login_redirect()

        user = authenticate(request, username=email, password=password)
        if user is None:
            existing_user = CustomUser.objects.filter(email__iexact=email).first()
            if existing_user:
                user = authenticate(
                    request,
                    username=existing_user.username,
                    password=password,
                )

        if user is None:
            messages.error(request, "Invalid email or password.")
            return _password_login_redirect()

        # Password authentication is retained only as an administrative fallback.
        if not user.is_platform_admin:
            messages.error(request, "Platform users must sign in with Google.")
            return _password_login_redirect()

        login(request, user)
        return redirect("admin_dashboard")

    google_login_enabled = bool(
        get_social_adapter(request).list_apps(request, provider="google")
    )
    return render(
        request,
        LOGIN_TEMPLATE,
        {"google_login_enabled": google_login_enabled},
    )


@login_required
def role_redirect_view(request):
    if request.user.is_authorized_user:
        return redirect(_destination_for(request.user))

    logout(request)
    messages.error(request, "Your account has not been provisioned for access.")
    return redirect("login")


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")

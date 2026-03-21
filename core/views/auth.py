from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.models import CustomUser
from core.roles import role_home_url_name


LOGIN_TEMPLATE = "core/auth/login.html"


def redirect_for_user(user):
    return redirect(role_home_url_name(getattr(user, "role", ""), is_superuser=getattr(user, "is_superuser", False)))


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not password:
            messages.error(request, "Password is required.")
            return redirect("login")

        user = authenticate(request, username=email, password=password)
        if not user:
            try:
                user_obj = CustomUser.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except CustomUser.DoesNotExist:
                user = None
        if not user:
            messages.error(request, "Invalid email or password.")
            return redirect("login")

        login(request, user)
        return redirect("role-redirect")
    return render(request, LOGIN_TEMPLATE)


@login_required
def role_redirect_view(request):
    return redirect_for_user(request.user)


def permission_denied_view(request, exception=None):
    if request.user.is_authenticated:
        return redirect_for_user(request.user)
    return render(request, "403.html", status=403)


@login_required
@require_POST
def switch_role_view(request):
    new_role = request.POST.get("role", "").strip()
    user = request.user
    valid_roles = user.roles or []
    assigned_roles = set(valid_roles + ([user.role] if user.role else []))

    if "admin" not in assigned_roles or len(assigned_roles) <= 1:
        messages.error(request, "Role switching is available only for admins with multiple assigned roles.")
        return redirect("role-redirect")

    if new_role not in valid_roles:
        messages.error(request, "You do not have that role.")
        return redirect("role-redirect")

    user.role = new_role
    user.save(update_fields=["role"])
    return redirect("role-redirect")

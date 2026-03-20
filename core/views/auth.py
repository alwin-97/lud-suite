from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.models import CustomUser


LOGIN_TEMPLATE = "core/auth/login.html"


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
    user = request.user

    if user.is_superuser or user.role == "admin":
        return redirect("admin_dashboard")
    if user.role == "mentor":
        return redirect("dashboard")
    if user.role == "mentee":
        return redirect("mentee_dashboard")
    if user.role == "endorser":
        return redirect("endorser_dashboard")
    if user.role == "reviewer":
        return redirect("mentor_mentee_list")
    return redirect("profile")


@login_required
@require_POST
def switch_role_view(request):
    new_role = request.POST.get("role", "").strip()
    user = request.user
    valid_roles = user.roles or []

    if new_role not in valid_roles:
        messages.error(request, "You do not have that role.")
        return redirect("role-redirect")

    user.role = new_role
    user.save(update_fields=["role"])
    return redirect("role-redirect")

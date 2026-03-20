from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

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

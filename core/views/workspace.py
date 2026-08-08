from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def workspace_home_view(request):
    if not request.user.is_authorized_user:
        logout(request)
        messages.error(request, "Your account has not been provisioned for access.")
        return redirect("login")
    if request.user.is_platform_admin:
        return redirect("admin_dashboard")

    memberships = request.user.cohort_memberships.filter(
        is_active=True,
        cohort__is_active=True,
        cohort__chapter__is_active=True,
        cohort__chapter__location__is_active=True,
    ).select_related("cohort", "cohort__chapter", "cohort__chapter__location")
    return render(
        request,
        "core/workspace/dashboard.html",
        {"memberships": memberships},
    )

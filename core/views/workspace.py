from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.models import ACTIVE_MEMBERSHIP_FILTER


@login_required
def workspace_home_view(request):
    if not request.user.is_authorized_user:
        logout(request)
        messages.error(request, "Your account has not been provisioned for access.")
        return redirect("login")
    if request.user.is_platform_admin:
        return redirect("admin_dashboard")

    memberships = request.user.cohort_memberships.filter(
        **ACTIVE_MEMBERSHIP_FILTER
    ).select_related(
        "cohort", "cohort__chapter", "cohort__chapter__location", "cohort__chapter__location__program"
    )
    return render(
        request,
        "core/workspace/dashboard.html",
        {"memberships": memberships},
    )

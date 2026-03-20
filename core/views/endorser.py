from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.decorators import role_required
from core.forms import WorkScheduleForm
from core.models import Activity, Notification
from core.views.common import User


ENDORSER_DASHBOARD_TEMPLATE = "core/endorser/dashboard.html"
ENDORSER_WORK_SCHEDULE_TEMPLATE = "core/endorser/work_schedule.html"
ENDORSER_PROFILE_TEMPLATE = "core/endorser/profile.html"
ENDORSER_PROFILE_EDIT_TEMPLATE = "core/endorser/profile_edit.html"
ENDORSER_ACTIVITY_LOG_TEMPLATE = "core/endorser/activity_log.html"
ENDORSER_MENTOR_ACTIVITY_TEMPLATE = "core/endorser/mentor_activity_list.html"


@role_required(allowed_roles=["endorser"])
def endorser_dashboard(request):
    return render(request, ENDORSER_DASHBOARD_TEMPLATE, {"active_page": "dashboard"})


@login_required
@role_required(allowed_roles=["endorser"])
def endorser_work_schedule(request):
    endorser = request.user

    if endorser.role != "endorser":
        messages.error(request, "You do not have permission to access this page.")
        return redirect("endorser_dashboard")

    if request.method == "POST":
        form = WorkScheduleForm(request.POST, endorser=endorser)
        if form.is_valid():
            work_schedule = form.save(commit=False)
            work_schedule.endorser = endorser
            work_schedule.save()
            form.save_m2m()

            for mentor in form.cleaned_data["mentors"]:
                Notification.objects.create(
                    message=f"New work schedule: {work_schedule.role} (Due {work_schedule.due_date})",
                    target_group="mentor",
                    created_by=endorser,
                )

            messages.success(request, "Work schedule sent successfully.", extra_tags="work_schedule")
            return redirect("endorser_work_schedule")
    else:
        form = WorkScheduleForm(endorser=endorser)

    return render(request, ENDORSER_WORK_SCHEDULE_TEMPLATE, {"form": form, "active_page": "schedule"})


@login_required
@role_required(allowed_roles=["endorser"])
def endorser_profile(request):
    if request.user.role != "endorser":
        return redirect("role-redirect")
    return render(request, ENDORSER_PROFILE_TEMPLATE, {"active_page": "profile"})


@login_required
@role_required(allowed_roles=["endorser"])
def endorser_edit_profile(request):
    if request.user.role != "endorser":
        return redirect("role-redirect")

    user = request.user
    if request.method == "POST":
        user.gender = request.POST.get("gender", user.gender)
        user.date_of_birth = request.POST.get("date_of_birth") or user.date_of_birth
        user.religion = request.POST.get("religion", user.religion)
        user.permanent_address = request.POST.get("permanent_address", user.permanent_address)
        user.institution = request.POST.get("institution", user.institution)
        user.designation = request.POST.get("designation", user.designation)

        if "profile_pic" in request.FILES:
            user.profile_pic = request.FILES["profile_pic"]

        user.save()
        return redirect("endorser_profile")

    return render(request, ENDORSER_PROFILE_EDIT_TEMPLATE, {"user": user, "active_page": "profile"})


@role_required(allowed_roles=["endorser"])
def activity_log(request):
    assigned_mentors = request.user.mentors.all()
    return render(request, ENDORSER_ACTIVITY_LOG_TEMPLATE, {"assigned_mentors": assigned_mentors, "active_page": "activity_log"})


@role_required(allowed_roles=["endorser"])
def mentor_activity_list(request, mentor_id):
    mentor = get_object_or_404(User, id=mentor_id, role="mentor")
    if not request.user.mentors.filter(id=mentor.id).exists():
        raise PermissionDenied("You are not allowed to access this mentor.")

    activities = Activity.objects.filter(user=mentor).order_by("-date")
    return render(
        request,
        ENDORSER_MENTOR_ACTIVITY_TEMPLATE,
        {"mentor": mentor, "activities": activities, "active_page": "activity_log"},
    )


@role_required(allowed_roles=["endorser"])
@require_POST
def add_remark(request):
    activity_id = request.POST.get("activity_id")
    remark = request.POST.get("remark", "")
    activity = get_object_or_404(Activity, id=activity_id)
    if not request.user.mentors.filter(id=activity.user_id).exists():
        return JsonResponse({"status": "error", "message": "Not allowed."}, status=403)
    activity.remark = remark
    activity.save()
    return JsonResponse({"activity_id": activity_id, "remark": remark, "status": "success"})

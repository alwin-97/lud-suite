from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.decorators import role_required
from core.forms import WorkScheduleAssignmentUpdateForm, WorkScheduleForm
from core.models import Activity, Notification, WorkSchedule, WorkScheduleAssignment
from core.views.common import User, role_layout_context


ENDORSER_DASHBOARD_TEMPLATE = "core/endorser/dashboard.html"
ENDORSER_WORK_SCHEDULE_TEMPLATE = "core/endorser/work_schedule.html"
ENDORSER_PROFILE_TEMPLATE = "core/endorser/profile.html"
ENDORSER_PROFILE_EDIT_TEMPLATE = "core/endorser/profile_edit.html"
ENDORSER_ACTIVITY_LOG_TEMPLATE = "core/endorser/activity_log.html"
ENDORSER_MENTOR_ACTIVITY_TEMPLATE = "core/endorser/mentor_activity_list.html"
ASSIGNED_WORK_ITEMS_TEMPLATE = "core/shared/work_items.html"
WORK_ITEMS_MANAGE_TEMPLATE = "core/endorser/work_schedule.html"
WORK_ITEM_ASSIGNEE_ROLES = ["endorser", "mentor", "mentee", "volunteer"]


def _sync_work_schedule_assignments(schedule, assignees):
    assignees = list(assignees)
    assignee_ids = {assignee.id for assignee in assignees}
    schedule.mentors.set(assignees)

    existing_assignments = {
        assignment.assignee_id: assignment
        for assignment in schedule.assignments.all()
    }

    for assignee in assignees:
        if assignee.id not in existing_assignments:
            WorkScheduleAssignment.objects.create(
                work_schedule=schedule,
                assignee=assignee,
            )

    schedule.assignments.exclude(assignee_id__in=assignee_ids).delete()


@role_required(allowed_roles=["endorser"])
def endorser_dashboard(request):
    assigned_mentors = request.user.mentors.all().order_by("first_name", "last_name", "username")
    mentor_activities = Activity.objects.filter(user__in=assigned_mentors)
    notifications_count = Notification.objects.filter(
        Q(target_group="endorser") | Q(target_group="all")
    ).count()
    context = {
        "assigned_mentors": assigned_mentors[:5],
        "assigned_mentor_count": assigned_mentors.count(),
        "mentor_activity_count": mentor_activities.count(),
        "remarked_activity_count": mentor_activities.exclude(Q(remark__isnull=True) | Q(remark="")).count(),
        "schedule_count": request.user.schedules.count(),
        "open_work_item_count": WorkScheduleAssignment.objects.filter(
            work_schedule__endorser=request.user,
            status__in=[WorkScheduleAssignment.Status.ASSIGNED, WorkScheduleAssignment.Status.IN_PROGRESS, WorkScheduleAssignment.Status.ON_HOLD],
        ).count(),
        "notification_count": notifications_count,
        "active_page": "dashboard",
    }
    return render(request, ENDORSER_DASHBOARD_TEMPLATE, context)


def _manage_work_items(request):
    creator = request.user
    created_schedules = (
        WorkSchedule.objects.filter(endorser=creator)
        .prefetch_related("assignments__assignee")
        .order_by("-due_date", "-id")
    )
    form_instance = None
    schedule_id = request.GET.get("edit")
    if schedule_id and schedule_id.isdigit():
        form_instance = get_object_or_404(WorkSchedule, id=int(schedule_id), endorser=creator)

    if request.method == "POST":
        schedule_id = request.POST.get("schedule_id", "").strip()
        schedule_instance = None
        if schedule_id.isdigit():
            schedule_instance = get_object_or_404(WorkSchedule, id=int(schedule_id), endorser=creator)
        form = WorkScheduleForm(request.POST, creator=creator, instance=schedule_instance)
        if form.is_valid():
            work_schedule = form.save(commit=False)
            work_schedule.endorser = creator
            work_schedule.save()
            assignees = form.cleaned_data["assignees"]
            _sync_work_schedule_assignments(work_schedule, assignees)

            for target_group in {assignee.role for assignee in assignees}:
                Notification.objects.create(
                    message=f"New work schedule: {work_schedule.role} (Due {work_schedule.due_date})",
                    target_group=target_group,
                    created_by=creator,
                )

            messages.success(
                request,
                "Work schedule updated successfully." if schedule_instance else "Work schedule sent successfully.",
                extra_tags="work_schedule",
            )
            return redirect("manage_work_items")
    else:
        form = WorkScheduleForm(creator=creator, instance=form_instance)

    context = {
        "form": form,
        "editing_schedule": form_instance,
        "created_schedules": created_schedules,
        "active_page": "work_schedule",
        "is_admin_workspace": creator.role == "admin",
    }
    context.update(role_layout_context(creator))
    return render(request, WORK_ITEMS_MANAGE_TEMPLATE, context)


@login_required
@role_required(allowed_roles=["admin", "endorser"])
def manage_work_items_view(request):
    return _manage_work_items(request)


@login_required
@role_required(allowed_roles=["endorser"])
def endorser_work_schedule(request):
    return _manage_work_items(request)


@login_required
@role_required(allowed_roles=["endorser"])
def endorser_profile(request):
    if request.user.role != "endorser":
        return redirect("role-redirect")
    return redirect("profile")


@login_required
@role_required(allowed_roles=["endorser"])
def endorser_edit_profile(request):
    if request.user.role != "endorser":
        return redirect("role-redirect")
    return redirect("profile_edit")


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


@login_required
@role_required(allowed_roles=WORK_ITEM_ASSIGNEE_ROLES)
def assigned_work_items_view(request):
    assignments = (
        WorkScheduleAssignment.objects.filter(assignee=request.user)
        .select_related("work_schedule", "work_schedule__endorser")
        .order_by("work_schedule__due_date", "-updated_at")
    )
    context = {
        "assignments": assignments,
        "active_page": "work_items",
    }
    context.update(role_layout_context(request.user))
    return render(request, ASSIGNED_WORK_ITEMS_TEMPLATE, context)


@login_required
@role_required(allowed_roles=WORK_ITEM_ASSIGNEE_ROLES)
@require_POST
def update_work_item_status_view(request, assignment_id):
    assignment = get_object_or_404(
        WorkScheduleAssignment.objects.select_related("assignee", "work_schedule"),
        id=assignment_id,
        assignee=request.user,
    )
    form = WorkScheduleAssignmentUpdateForm(request.POST, instance=assignment)
    if form.is_valid():
        form.save()
        messages.success(request, "Work item status updated.")
    else:
        messages.error(request, "Could not update work item status.")
    return redirect("assigned_work_items")

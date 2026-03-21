from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.decorators import role_required
from core.forms import ProfileArtifactForm
from core.models import (
    Activity,
    ApprovalLog,
    Chapter,
    CustomUser,
    DiaryEntry,
    EvidenceAttachment,
    Notification,
    ProfileArtifact,
    ReflectiveReport,
    VolunteerTranscript,
)
from core.roles import REVIEW_ACCESS_ROLES, REVIEWER_ROLES
from core.views.common import role_layout_context, user_notification_groups, volunteer_reporting_assignment_for

VOLUNTEER_DASHBOARD_TEMPLATE = "core/workspace/volunteer_dashboard.html"
APPROVAL_DASHBOARD_TEMPLATE = "core/workspace/approval_dashboard.html"
APPROVAL_QUEUE_TEMPLATE = "core/workspace/approval_queue.html"
VOLUNTEER_PUBLIC_PROFILE_TEMPLATE = "core/workspace/volunteer_public_profile.html"
VOLUNTEER_INTERNAL_PROFILE_TEMPLATE = "core/workspace/volunteer_internal_profile.html"
NOTIFICATIONS_TEMPLATE = "core/shared/notifications.html"

TRANSCRIPT_TEMPLATE_CHOICES = [
    "Volunteer Service Summary",
    "Leadership Transcript",
    "Programme Completion Transcript",
]


def _as_decimal(value):
    return value if value is not None else Decimal("0")


def _is_final_approver(user):
    return user.role == "admin"


def _review_scope_location_ids(user):
    if user.role in REVIEWER_ROLES and Chapter.objects.filter(leader=user).exists():
        return list(
            Chapter.objects.filter(leader=user)
            .exclude(location__isnull=True)
            .values_list("location_id", flat=True)
            .distinct()
        )
    return None


def _scope_location_queryset(queryset, user, field_name="location_id"):
    location_ids = _review_scope_location_ids(user)
    if location_ids is None:
        return queryset
    if not location_ids:
        return queryset.none()
    return queryset.filter(**{f"{field_name}__in": location_ids})


def _scoped_transcript_queryset(user, queryset=None):
    if queryset is None:
        queryset = VolunteerTranscript.objects.all()
    location_ids = _review_scope_location_ids(user)
    if location_ids is None:
        return queryset
    if not location_ids:
        return queryset.none()

    volunteer_ids = set(
        ReflectiveReport.objects.filter(location_id__in=location_ids).values_list("user_id", flat=True)
    )
    volunteer_ids.update(
        DiaryEntry.objects.filter(location_id__in=location_ids).values_list("volunteer_id", flat=True)
    )
    return queryset.filter(volunteer_id__in=volunteer_ids)


def _ensure_report_in_scope(report, user):
    location_ids = _review_scope_location_ids(user)
    if location_ids is not None and report.location_id not in location_ids:
        raise PermissionDenied("You are not allowed to review this report.")


def _ensure_diary_in_scope(diary, user):
    location_ids = _review_scope_location_ids(user)
    if location_ids is not None and diary.location_id not in location_ids:
        raise PermissionDenied("You are not allowed to review this diary.")


def _ensure_transcript_in_scope(transcript, user):
    location_ids = _review_scope_location_ids(user)
    if location_ids is None:
        return
    if not location_ids:
        raise PermissionDenied("You are not allowed to review this transcript.")
    volunteer_id = transcript.volunteer_id
    in_scope = ReflectiveReport.objects.filter(user_id=volunteer_id, location_id__in=location_ids).exists() or DiaryEntry.objects.filter(
        volunteer_id=volunteer_id, location_id__in=location_ids
    ).exists()
    if not in_scope:
        raise PermissionDenied("You are not allowed to review this transcript.")


def _evidence_attachments_for_volunteer(volunteer):
    report_ids = list(ReflectiveReport.objects.filter(user=volunteer).values_list("id", flat=True))
    diary_ids = list(DiaryEntry.objects.filter(volunteer=volunteer).values_list("id", flat=True))
    transcript_ids = list(VolunteerTranscript.objects.filter(volunteer=volunteer).values_list("id", flat=True))
    artifact_ids = list(ProfileArtifact.objects.filter(user=volunteer).values_list("id", flat=True))
    evidence_filter = Q(linked_model="ReflectiveReport", linked_id__in=report_ids) | Q(
        linked_model="DiaryEntry", linked_id__in=diary_ids
    )
    evidence_filter |= Q(linked_model="VolunteerTranscript", linked_id__in=transcript_ids)
    evidence_filter |= Q(linked_model="ProfileArtifact", linked_id__in=artifact_ids)
    return EvidenceAttachment.objects.filter(evidence_filter).select_related("asset").order_by("-created_at")


def build_transcript_summary(volunteer):
    activity_records = list(Activity.objects.filter(user=volunteer).order_by("-date"))
    approved_reports = list(
        ReflectiveReport.objects.filter(user=volunteer, status="Approved")
        .select_related("location", "programme")
        .order_by("-date")
    )
    approved_diaries = list(
        DiaryEntry.objects.filter(volunteer=volunteer, review_status="Approved")
        .select_related("location")
        .order_by("-date")
    )

    profile_artifacts = list(ProfileArtifact.objects.filter(user=volunteer).order_by("-created_at"))
    evidence_attachments = list(_evidence_attachments_for_volunteer(volunteer))

    if not approved_reports and not approved_diaries and not activity_records:
        return ""

    total_report_hours = sum((_as_decimal(item.duration) for item in approved_reports), Decimal("0"))
    total_diary_hours = sum((_as_decimal(item.duration) for item in approved_diaries), Decimal("0"))

    activities = []
    for report in approved_reports:
        if report.activity_name:
            activities.append(report.activity_name)
    for diary in approved_diaries:
        if diary.linked_activity:
            activities.append(diary.linked_activity)
    for activity in activity_records:
        if activity.activity:
            activities.append(activity.activity)
    unique_activities = list(dict.fromkeys([item for item in activities if item]))

    locations = []
    for report in approved_reports:
        if report.location:
            locations.append(report.location.name)
    for diary in approved_diaries:
        if diary.location:
            locations.append(diary.location.name)
    unique_locations = list(dict.fromkeys(locations))

    highlights = []
    for report in approved_reports[:2]:
        if report.learnings:
            highlights.append(report.learnings.strip())
    for diary in approved_diaries[:2]:
        if diary.narrative_entry:
            highlights.append(diary.narrative_entry.strip())
    for activity in activity_records[:2]:
        if activity.learnings:
            highlights.append(activity.learnings.strip())

    summary_parts = [
        f"{volunteer.get_full_name() or volunteer.username} has contributed through {len(approved_reports)} approved reflective reports, {len(approved_diaries)} approved diary entries, and {len(activity_records)} tracked activity records.",
        f"The recorded contribution adds up to {total_report_hours + total_diary_hours} documented hours across programme activity.",
    ]
    if unique_activities:
        summary_parts.append(f"Key activities include {', '.join(unique_activities[:5])}.")
    if unique_locations:
        summary_parts.append(f"Documented contributions span {', '.join(unique_locations[:4])}.")
    if highlights:
        summary_parts.append(f"Highlights from the approved record set: {' '.join(highlights[:2])[:420]}")
    if profile_artifacts:
        summary_parts.append(f"{len(profile_artifacts)} profile artifact(s) are available as supporting evidence.")
    if evidence_attachments:
        summary_parts.append(f"{len(evidence_attachments)} repository-linked evidence attachment(s) support this transcript.")

    return " ".join(summary_parts)


def build_transcript_export_body(transcript):
    volunteer = transcript.volunteer
    approved_reports = ReflectiveReport.objects.filter(user=volunteer, status="Approved").order_by("-date")
    approved_diaries = DiaryEntry.objects.filter(volunteer=volunteer, review_status="Approved").order_by("-date")
    activity_records = Activity.objects.filter(user=volunteer).order_by("-date")
    profile_artifacts = ProfileArtifact.objects.filter(user=volunteer).order_by("-created_at")
    evidence_attachments = _evidence_attachments_for_volunteer(volunteer)

    evidence_titles = [attachment.asset.title for attachment in evidence_attachments[:10]]
    return "\n".join(
        [
            f"Volunteer Transcript: {transcript.template_choice}",
            f"Volunteer: {volunteer.get_full_name() or volunteer.username}",
            f"Status: {transcript.get_approval_status_display()}",
            "",
            "Summary",
            transcript.generated_summary,
            "",
            "Record Counts",
            f"Approved reflective reports: {approved_reports.count()}",
            f"Approved work diaries: {approved_diaries.count()}",
            f"Tracked activities: {activity_records.count()}",
            f"Profile artifacts: {profile_artifacts.count()}",
            f"Repository-linked evidence: {evidence_attachments.count()}",
            "",
            "Evidence Index",
            *([f"- {title}" for title in evidence_titles] or ["- No repository-linked evidence recorded."]),
            "",
            f"Approval Notes: {transcript.reviewer_notes or 'Approved without additional notes.'}",
        ]
    )


def _create_group_notification(created_by, target_group, subject, message):
    Notification.objects.create(
        created_by=created_by,
        target_group=target_group,
        subject=subject,
        message=message,
    )


def _create_notifications(created_by, target_groups, subject, message):
    seen = set()
    for group in target_groups:
        if group and group not in seen:
            _create_group_notification(created_by, group, subject, message)
            seen.add(group)


def _report_queue_queryset(user):
    statuses = ["Submitted", "Reviewed"] if _is_final_approver(user) else ["Submitted"]
    return _scope_location_queryset(
        ReflectiveReport.objects.filter(status__in=statuses).select_related("user", "location", "programme"),
        user,
    )


def _diary_queue_queryset(user):
    statuses = ["Submitted", "Reviewed"] if _is_final_approver(user) else ["Submitted"]
    return _scope_location_queryset(
        DiaryEntry.objects.filter(review_status__in=statuses).select_related("volunteer", "location"),
        user,
    )


def _transcript_queue_queryset(user):
    if user.role not in REVIEWER_ROLES:
        return VolunteerTranscript.objects.none()
    statuses = ["Pending Review"]
    return _scoped_transcript_queryset(
        user,
        VolunteerTranscript.objects.filter(approval_status__in=statuses).select_related("volunteer"),
    )


@login_required
@role_required(allowed_roles=["volunteer"])
def volunteer_dashboard_view(request):
    artifact_form = ProfileArtifactForm()
    if request.method == "POST":
        artifact_form = ProfileArtifactForm(request.POST, request.FILES)
        if artifact_form.is_valid():
            artifact = artifact_form.save(commit=False)
            artifact.user = request.user
            artifact.save()
            messages.success(request, "Profile artifact uploaded.")
            return redirect("volunteer_dashboard")

    diaries = DiaryEntry.objects.filter(volunteer=request.user).order_by("-date")
    reports = ReflectiveReport.objects.filter(user=request.user).order_by("-date")
    transcripts = VolunteerTranscript.objects.filter(volunteer=request.user).order_by("-created_at")
    artifacts = ProfileArtifact.objects.filter(user=request.user).order_by("-created_at")
    reporting_assignment = volunteer_reporting_assignment_for(request.user)

    context = {
        "artifact_form": artifact_form,
        "diary_count": diaries.count(),
        "report_count": reports.count(),
        "submitted_diary_count": diaries.filter(review_status__in=["Submitted", "Reviewed"]).count(),
        "submitted_report_count": reports.filter(status__in=["Submitted", "Reviewed"]).count(),
        "approved_transcript_count": transcripts.filter(approval_status="Approved").count(),
        "public_artifact_count": artifacts.filter(is_public=True).count(),
        "recent_diaries": diaries[:5],
        "recent_reports": reports[:5],
        "recent_transcripts": transcripts[:5],
        "recent_artifacts": artifacts[:5],
        "reporting_assignment": reporting_assignment,
        "active_page": "dashboard",
        "public_profile_user": request.user,
    }
    context.update(role_layout_context(request.user))
    return render(request, VOLUNTEER_DASHBOARD_TEMPLATE, context)


@login_required
@role_required(allowed_roles=REVIEW_ACCESS_ROLES)
def approval_dashboard_view(request):
    pending_reports = _report_queue_queryset(request.user).count()
    pending_diaries = _diary_queue_queryset(request.user).count()
    pending_transcripts = _transcript_queue_queryset(request.user).count()

    context = {
        "pending_reports": pending_reports,
        "pending_diaries": pending_diaries,
        "pending_transcripts": pending_transcripts,
        "recent_reports": _report_queue_queryset(request.user)[:5],
        "recent_diaries": _diary_queue_queryset(request.user)[:5],
        "recent_transcripts": _transcript_queue_queryset(request.user)[:5],
        "is_final_approver": _is_final_approver(request.user),
        "active_page": "review_dashboard",
    }
    context.update(role_layout_context(request.user))
    return render(request, APPROVAL_DASHBOARD_TEMPLATE, context)


@login_required
@role_required(allowed_roles=REVIEW_ACCESS_ROLES)
def approval_queue_view(request):
    record_filter = request.GET.get("record", "all")
    search = request.GET.get("q", "").strip()

    reports = _report_queue_queryset(request.user)
    diaries = _diary_queue_queryset(request.user)
    transcripts = _transcript_queue_queryset(request.user)

    if search:
        reports = reports.filter(Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search) | Q(activity_name__icontains=search))
        diaries = diaries.filter(Q(volunteer__first_name__icontains=search) | Q(volunteer__last_name__icontains=search) | Q(linked_activity__icontains=search))
        transcripts = transcripts.filter(Q(volunteer__first_name__icontains=search) | Q(volunteer__last_name__icontains=search) | Q(template_choice__icontains=search))

    context = {
        "record_filter": record_filter,
        "search": search,
        "reports": reports if record_filter in ("all", "reports") else [],
        "diaries": diaries if record_filter in ("all", "diaries") else [],
        "transcripts": transcripts if record_filter in ("all", "transcripts") else [],
        "is_final_approver": _is_final_approver(request.user),
        "active_page": "approval_queue",
    }
    context.update(role_layout_context(request.user))
    return render(request, APPROVAL_QUEUE_TEMPLATE, context)


@login_required
@role_required(allowed_roles=REVIEW_ACCESS_ROLES)
@require_POST
def review_reflective_report_view(request, report_id):
    report = get_object_or_404(ReflectiveReport, id=report_id)
    _ensure_report_in_scope(report, request.user)
    action = request.POST.get("action", "").strip().lower()
    comments = request.POST.get("comments", "").strip()

    if action not in {"approve", "return"}:
        messages.error(request, "Invalid review action.")
        return redirect("approval_queue")

    if action == "approve":
        report.status = "Approved" if _is_final_approver(request.user) else "Reviewed"
    else:
        report.status = "Returned"
    report.save(update_fields=["status", "updated_at"])
    ApprovalLog.objects.create(
        record_type="reflective_report",
        record_id=report.id,
        reviewer=request.user,
        decision=(
            "approved"
            if action == "approve" and _is_final_approver(request.user)
            else "escalated"
            if action == "approve"
            else "returned"
        ),
        comments=comments,
    )
    if action == "approve" and _is_final_approver(request.user):
        _create_group_notification(
            request.user,
            "volunteer",
            "Reflective report approved",
            f"Reflective report '{report.activity_name}' was approved by {request.user.get_full_name() or request.user.username}.",
        )
        messages.success(request, "Reflective report approved.")
    elif action == "approve":
        _create_group_notification(
            request.user,
            "admin",
            "Reflective report awaiting final approval",
            f"Reflective report '{report.activity_name}' was reviewed by {request.user.get_full_name() or request.user.username} and is ready for final approval.",
        )
        messages.success(request, "Reflective report reviewed and forwarded to admin.")
    else:
        _create_group_notification(
            request.user,
            "volunteer",
            "Reflective report returned",
            f"Reflective report '{report.activity_name}' was returned by {request.user.get_full_name() or request.user.username}.",
        )
        messages.success(request, "Reflective report returned.")
    return redirect("approval_queue")


@login_required
@role_required(allowed_roles=REVIEW_ACCESS_ROLES)
@require_POST
def review_work_diary_view(request, diary_id):
    diary = get_object_or_404(DiaryEntry, id=diary_id)
    _ensure_diary_in_scope(diary, request.user)
    action = request.POST.get("action", "").strip().lower()
    comments = request.POST.get("comments", "").strip()

    if action not in {"approve", "return"}:
        messages.error(request, "Invalid review action.")
        return redirect("approval_queue")

    if action == "approve":
        diary.review_status = "Approved" if _is_final_approver(request.user) else "Reviewed"
    else:
        diary.review_status = "Returned"
    diary.save(update_fields=["review_status", "updated_at"])
    ApprovalLog.objects.create(
        record_type="work_diary",
        record_id=diary.id,
        reviewer=request.user,
        decision=(
            "approved"
            if action == "approve" and _is_final_approver(request.user)
            else "escalated"
            if action == "approve"
            else "returned"
        ),
        comments=comments,
    )
    if action == "approve" and _is_final_approver(request.user):
        _create_group_notification(
            request.user,
            "volunteer",
            "Work diary approved",
            f"Diary entry on {diary.date:%Y-%m-%d} was approved by {request.user.get_full_name() or request.user.username}.",
        )
        messages.success(request, "Work diary approved.")
    elif action == "approve":
        _create_group_notification(
            request.user,
            "admin",
            "Work diary awaiting final approval",
            f"Diary entry on {diary.date:%Y-%m-%d} was reviewed by {request.user.get_full_name() or request.user.username} and is ready for final approval.",
        )
        messages.success(request, "Work diary reviewed and forwarded to admin.")
    else:
        _create_group_notification(
            request.user,
            "volunteer",
            "Work diary returned",
            f"Diary entry on {diary.date:%Y-%m-%d} was returned by {request.user.get_full_name() or request.user.username}.",
        )
        messages.success(request, "Work diary returned for updates.")
    return redirect("approval_queue")


@login_required
@role_required(allowed_roles=REVIEWER_ROLES)
@require_POST
def review_transcript_view(request, transcript_id):
    transcript = get_object_or_404(VolunteerTranscript, id=transcript_id)
    _ensure_transcript_in_scope(transcript, request.user)
    action = request.POST.get("action", "").strip().lower()
    comments = request.POST.get("comments", "").strip()

    if action not in {"approve", "return"}:
        messages.error(request, "Invalid review action.")
        return redirect("transcript")
    if transcript.approval_status != "Pending Review":
        messages.error(request, "This transcript is not waiting for reviewer action.")
        return redirect("transcript")

    if action == "approve":
        transcript.approval_status = "Approved"
    else:
        transcript.approval_status = "Draft"
    transcript.reviewer_notes = comments
    if action == "approve" and not transcript.export_file:
        export_body = build_transcript_export_body(transcript)
        transcript.export_file.save(
            f"transcript_{transcript.id or 'draft'}.txt",
            ContentFile(export_body.encode("utf-8")),
            save=False,
        )
    elif action == "return":
        transcript.export_file = None
    transcript.save(update_fields=["approval_status", "reviewer_notes", "export_file", "updated_at"])
    ApprovalLog.objects.create(
        record_type="transcript",
        record_id=transcript.id,
        reviewer=request.user,
        decision="approved" if action == "approve" else "returned",
        comments=comments,
    )
    if action == "approve":
        reviewer_name = request.user.get_full_name() or request.user.username
        _create_group_notification(
            request.user,
            "volunteer",
            "Transcript approved",
            f"Transcript '{transcript.template_choice}' was approved by {reviewer_name}.",
        )
        _create_group_notification(
            request.user,
            "admin",
            "Transcript ready for export",
            f"Transcript '{transcript.template_choice}' for {transcript.volunteer.get_full_name() or transcript.volunteer.username} was approved by {reviewer_name} and is ready for admin download.",
        )
        messages.success(request, "Transcript approved and published for export.")
    else:
        _create_group_notification(
            request.user,
            "volunteer",
            "Transcript returned",
            f"Transcript '{transcript.template_choice}' for {transcript.volunteer.get_full_name() or transcript.volunteer.username} was returned by {request.user.get_full_name() or request.user.username}.",
        )
        messages.success(request, "Transcript returned.")
    return redirect("transcript")


@login_required
@role_required(allowed_roles=["volunteer"])
@require_POST
def generate_transcript_view(request):
    template_choice = request.POST.get("template_choice", "").strip() or TRANSCRIPT_TEMPLATE_CHOICES[0]

    if template_choice not in TRANSCRIPT_TEMPLATE_CHOICES:
        messages.error(request, "Invalid transcript template.")
        return redirect("transcript")

    generated_summary = build_transcript_summary(request.user)
    if not generated_summary:
        messages.error(request, "Transcript generation requires at least one approved report, approved diary, or tracked activity.")
        return redirect("transcript")

    VolunteerTranscript.objects.create(
        volunteer=request.user,
        template_choice=template_choice,
        generated_summary=generated_summary,
        approval_status="Pending Review",
    )
    _create_notifications(
        request.user,
        REVIEWER_ROLES,
        "Transcript awaiting review",
        f"A volunteer transcript draft for {request.user.get_full_name() or request.user.username} is pending review.",
    )
    messages.success(request, "Transcript draft generated and submitted for review.")
    return redirect("transcript")


@login_required
def volunteer_public_profile_view(request, user_id):
    volunteer = get_object_or_404(CustomUser, id=user_id)
    if volunteer.role != "volunteer" and "volunteer" not in (volunteer.roles or []):
        return redirect("role-redirect")

    context = {
        "volunteer_profile": volunteer,
        "artifacts": ProfileArtifact.objects.filter(user=volunteer, is_public=True).order_by("-created_at"),
        "approved_transcripts": VolunteerTranscript.objects.filter(volunteer=volunteer, approval_status="Approved").order_by("-created_at"),
        "approved_reports_count": ReflectiveReport.objects.filter(user=volunteer, status="Approved").count(),
        "approved_diaries_count": DiaryEntry.objects.filter(volunteer=volunteer, review_status="Approved").count(),
        "active_page": "public_profile",
    }
    context.update(role_layout_context(request.user))
    return render(request, VOLUNTEER_PUBLIC_PROFILE_TEMPLATE, context)


@login_required
@role_required(allowed_roles=REVIEW_ACCESS_ROLES)
def volunteer_internal_profile_view(request, user_id):
    volunteer = get_object_or_404(CustomUser, id=user_id)
    if volunteer.role != "volunteer" and "volunteer" not in (volunteer.roles or []):
        return redirect("role-redirect")

    context = {
        "volunteer_profile": volunteer,
        "artifacts": ProfileArtifact.objects.filter(user=volunteer).order_by("-created_at"),
        "transcripts": VolunteerTranscript.objects.filter(volunteer=volunteer).order_by("-created_at"),
        "reports": ReflectiveReport.objects.filter(user=volunteer).order_by("-date")[:10],
        "diaries": DiaryEntry.objects.filter(volunteer=volunteer).order_by("-date")[:10],
        "active_page": "volunteer_profiles",
    }
    context.update(role_layout_context(request.user))
    return render(request, VOLUNTEER_INTERNAL_PROFILE_TEMPLATE, context)


@login_required
def notification_center_view(request):
    groups = user_notification_groups(request.user)
    notifications = Notification.objects.filter(target_group__in=groups).order_by("-created_at")[:100]
    context = {
        "notifications": notifications,
        "active_page": "notifications",
    }
    context.update(role_layout_context(request.user))
    return render(request, NOTIFICATIONS_TEMPLATE, context)

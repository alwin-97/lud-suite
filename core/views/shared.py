from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.decorators import role_required
from core.models import DiaryEntry, ProfileArtifact, ReflectiveReport, RepositoryAsset, VolunteerTranscript
from core.forms import DiaryEntryForm, ReflectiveReportForm, RepositoryAssetForm
from core.roles import REVIEW_ACCESS_ROLES, REVIEWER_ROLES
from core.views.common import role_layout_context, volunteer_reporting_assignment_for
from core.views.workspace import TRANSCRIPT_TEMPLATE_CHOICES, _scoped_transcript_queryset


PROFILE_TEMPLATE = "core/shared/profile.html"
PROFILE_EDIT_TEMPLATE = "core/shared/profile_edit.html"
WORKFLOW_GUIDE_TEMPLATE = "core/shared/workflow_guide.html"
WORK_DIARY_LIST_TEMPLATE = "core/shared/work_diary_list.html"
REFLECTIVE_REPORT_LIST_TEMPLATE = "core/shared/reflective_report_list.html"


@login_required
def profile_view(request):
    context = {"user": request.user, "active_page": "profile"}
    context.update(role_layout_context(request.user))
    return render(request, PROFILE_TEMPLATE, context)


@login_required
@role_required(allowed_roles=["volunteer"])
def work_diary_view(request):
    reporting_assignment = volunteer_reporting_assignment_for(request.user)

    def selected_status():
        return "Submitted" if request.POST.get("submit_action") == "submit" else "Draft"

    if request.method == "POST":
        form = DiaryEntryForm(request.POST, request.FILES, user=request.user)
        if not reporting_assignment:
            messages.error(request, "Admin must assign your reporting location before you can submit a work diary.")
            return redirect("work_diary")
        if form.is_valid():
            entry = form.save(commit=False)
            entry.volunteer = request.user
            entry.location = reporting_assignment.location
            entry.review_status = selected_status()
            entry.save()
            if entry.review_status == "Submitted":
                messages.success(request, "Work diary entry submitted for review.")
            else:
                messages.success(request, "Work diary entry saved as draft.")
            return redirect("work_diary")
    else:
        form = DiaryEntryForm(user=request.user)
    
    entries = DiaryEntry.objects.filter(volunteer=request.user).order_by("-date", "-created_at")[:5]
    context = {
        "form": form,
        "entries": entries,
        "reporting_assignment": reporting_assignment,
        "active_page": "work_diary"
    }
    context.update(role_layout_context(request.user))
    return render(request, "core/shared/work_diary.html", context)


@login_required
@role_required(allowed_roles=["volunteer"])
def work_diary_list_view(request):
    entries = DiaryEntry.objects.filter(volunteer=request.user).order_by("-date", "-created_at")
    context = {
        "entries": entries,
        "active_page": "work_diary",
    }
    context.update(role_layout_context(request.user))
    return render(request, WORK_DIARY_LIST_TEMPLATE, context)

@login_required
@role_required(allowed_roles=["volunteer"])
def reflective_report_view(request):
    def reporter_identifier_for(user):
        mentee_profile = getattr(user, "mentee_profile_safe", None)
        if mentee_profile and mentee_profile.register_no:
            return mentee_profile.register_no
        return user.username

    def selected_status():
        return "Submitted" if request.POST.get("submit_action") == "submit" else "Draft"

    reporting_assignment = volunteer_reporting_assignment_for(request.user)

    if request.method == "POST":
        form = ReflectiveReportForm(request.POST, request.FILES, user=request.user)
        if not reporting_assignment:
            messages.error(request, "Admin must assign your programme, location, and endorser before you can submit a reflective report.")
            return redirect("reflective_report")
        elif form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.programme = reporting_assignment.programme
            report.location = reporting_assignment.location
            report.endorser = reporting_assignment.endorser
            report.reporter_name = request.user.get_full_name()
            report.reporter_email = request.user.email
            report.reporter_identifier = reporter_identifier_for(request.user)
            report.reporter_class_role = request.user.get_role_display()
            report.status = selected_status()
            report.save()
            if report.status == "Submitted":
                messages.success(request, "Reflective report submitted for review.")
            else:
                messages.success(request, "Reflective report saved as draft.")
            return redirect("reflective_report")
    else:
        form = ReflectiveReportForm(user=request.user)
        
    reports = ReflectiveReport.objects.filter(user=request.user).order_by("-date", "-created_at")[:5]
    context = {
        "form": form,
        "reports": reports,
        "reporter_name": request.user.get_full_name(),
        "reporter_email": request.user.email,
        "reporter_identifier": reporter_identifier_for(request.user),
        "reporter_role": request.user.get_role_display(),
        "reporting_assignment": reporting_assignment,
        "active_page": "reflective_report"
    }
    context.update(role_layout_context(request.user))
    return render(request, "core/shared/reflective_report.html", context)


@login_required
@role_required(allowed_roles=["volunteer"])
def reflective_report_list_view(request):
    def reporter_identifier_for(user):
        mentee_profile = getattr(user, "mentee_profile_safe", None)
        if mentee_profile and mentee_profile.register_no:
            return mentee_profile.register_no
        return user.username

    reports = ReflectiveReport.objects.filter(user=request.user).order_by("-date", "-created_at")
    context = {
        "reports": reports,
        "reporter_name": request.user.get_full_name(),
        "reporter_email": request.user.email,
        "reporter_identifier": reporter_identifier_for(request.user),
        "reporter_role": request.user.get_role_display(),
        "active_page": "reflective_report",
    }
    context.update(role_layout_context(request.user))
    return render(request, REFLECTIVE_REPORT_LIST_TEMPLATE, context)

@login_required
def repository_view(request):
    if request.method == "POST":
        form = RepositoryAssetForm(request.POST, request.FILES)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.uploaded_by = request.user
            asset.save()
            return redirect("repository")
    else:
        form = RepositoryAssetForm()

    # Extract user roles since the system uses an array
    user_roles = request.user.roles or []
    if request.user.role and request.user.role not in user_roles:
        user_roles.append(request.user.role)

    if request.user.role == "admin":
        assets = RepositoryAsset.objects.all().prefetch_related("attachments")
    else:
        assets = (
            RepositoryAsset.objects.filter(is_active=True)
            .filter(
                Q(role_visibility='all') |
                Q(role_visibility__in=user_roles) |
                Q(uploaded_by=request.user)
            )
            .prefetch_related("attachments")
            .distinct()
        )

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    if query:
        assets = assets.filter(
            Q(title__icontains=query) |
            Q(category__icontains=query) |
            Q(tags__icontains=query)
        )
    if category:
        assets = assets.filter(category__iexact=category)

    categories = (
        RepositoryAsset.objects.filter(id__in=assets.values_list("id", flat=True))
        .order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )

    context = {
        "form": form,
        "assets": assets,
        "categories": categories,
        "search": query,
        "selected_category": category,
        "can_manage_repository": request.user.role == "admin",
        "active_page": "repository"
    }
    context.update(role_layout_context(request.user))
    return render(request, "core/shared/repository.html", context)


@login_required
@role_required(allowed_roles=["admin"])
@require_POST
def toggle_repository_asset_status_view(request, asset_id):
    asset = get_object_or_404(RepositoryAsset, id=asset_id)
    asset.is_active = not asset.is_active
    asset.save(update_fields=["is_active", "updated_at"])
    messages.success(
        request,
        f"Repository asset '{asset.title}' has been {'enabled' if asset.is_active else 'disabled'}.",
    )
    return redirect("repository")


@login_required
@role_required(allowed_roles=["volunteer", *REVIEW_ACCESS_ROLES])
def transcript_view(request):
    if request.user.role == 'volunteer':
        transcripts = VolunteerTranscript.objects.filter(volunteer=request.user)
    else:
        transcripts = _scoped_transcript_queryset(request.user)

    assigned_roles = set(request.user.roles or [])
    if request.user.role:
        assigned_roles.add(request.user.role)

    context = {
        "transcripts": transcripts,
        "transcript_templates": TRANSCRIPT_TEMPLATE_CHOICES,
        "can_generate_transcript": "volunteer" in assigned_roles and request.user.role == "volunteer",
        "can_review_transcript": request.user.role in REVIEWER_ROLES,
        "show_transcript_owner": request.user.role != "volunteer",
        "is_admin_transcript_view": request.user.role == "admin",
        "active_page": "transcript",
    }
    context.update(role_layout_context(request.user))
    return render(request, "core/shared/transcript.html", context)


def settings_view(request):
    return HttpResponse("Settings Page")


@login_required
def workflow_guide_view(request):
    context = {"active_page": "workflow"}
    context.update(role_layout_context(request.user))
    return render(request, WORKFLOW_GUIDE_TEMPLATE, context)


@login_required
def profile_edit(request):
    user = request.user

    if request.method == "POST":
        user.gender = request.POST.get("gender")
        user.date_of_birth = request.POST.get("date_of_birth") or None
        user.religion = request.POST.get("religion")
        user.phone = request.POST.get("phone")
        user.permanent_address = request.POST.get("permanent_address")
        user.institution = request.POST.get("institution")
        user.designation = request.POST.get("designation")
        profile_pic = request.FILES.get("profile_pic")
        if profile_pic:
            user.profile_pic = profile_pic
        user.save()
        return redirect("profile")

    context = {"user": user, "active_page": "profile"}
    context.update(role_layout_context(request.user))
    return render(request, PROFILE_EDIT_TEMPLATE, context)

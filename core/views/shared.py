from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render

from core.models import DiaryEntry, ReflectiveReport, VolunteerTranscript, RepositoryAsset
from core.forms import DiaryEntryForm, ReflectiveReportForm, VolunteerTranscriptForm, RepositoryAssetForm


PROFILE_TEMPLATE = "core/shared/profile.html"
PROFILE_EDIT_TEMPLATE = "core/shared/profile_edit.html"
WORKFLOW_GUIDE_TEMPLATE = "core/shared/workflow_guide.html"


@login_required
def profile_view(request):
    return render(request, PROFILE_TEMPLATE, {"user": request.user, "active_page": "profile"})


@login_required
def work_diary_view(request):
    if request.method == "POST":
        form = DiaryEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.volunteer = request.user
            entry.save()
            return redirect("work_diary")
    else:
        form = DiaryEntryForm()
    
    entries = DiaryEntry.objects.filter(volunteer=request.user)
    return render(request, "core/shared/work_diary.html", {
        "form": form,
        "entries": entries,
        "active_page": "work_diary"
    })

@login_required
def reflective_report_view(request):
    if request.method == "POST":
        form = ReflectiveReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()
            return redirect("reflective_report")
    else:
        form = ReflectiveReportForm()
        
    reports = ReflectiveReport.objects.filter(user=request.user)
    return render(request, "core/shared/reflective_report.html", {
        "form": form,
        "reports": reports,
        "active_page": "reflective_report"
    })

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
    
    assets = RepositoryAsset.objects.filter(
        Q(role_visibility='all') |
        Q(role_visibility__in=user_roles) |
        Q(uploaded_by=request.user)
    ).distinct()

    return render(request, "core/shared/repository.html", {
        "form": form,
        "assets": assets,
        "active_page": "repository"
    })


def notification_view(request):
    return HttpResponse("Notification Page")


@login_required
def transcript_view(request):
    if request.user.role == 'volunteer':
        transcripts = VolunteerTranscript.objects.filter(volunteer=request.user)
    else:
        transcripts = VolunteerTranscript.objects.all()

    return render(request, "core/shared/transcript.html", {
        "transcripts": transcripts,
        "active_page": "transcript"
    })


def settings_view(request):
    return HttpResponse("Settings Page")


@login_required
def workflow_guide_view(request):
    return render(request, WORKFLOW_GUIDE_TEMPLATE, {"active_page": "workflow"})


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

    return render(request, PROFILE_EDIT_TEMPLATE, {"user": user, "active_page": "profile"})

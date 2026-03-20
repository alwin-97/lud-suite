from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render


PROFILE_TEMPLATE = "core/shared/profile.html"
PROFILE_EDIT_TEMPLATE = "core/shared/profile_edit.html"
WORKFLOW_GUIDE_TEMPLATE = "core/shared/workflow_guide.html"


@login_required
def profile_view(request):
    return render(request, PROFILE_TEMPLATE, {"user": request.user})


def work_diary_view(request):
    return HttpResponse("Work Diary Page")


def repository_view(request):
    return HttpResponse("Data Repository Page")


def notification_view(request):
    return HttpResponse("Notification Page")


def transcript_view(request):
    return HttpResponse("Transcript Page")


def settings_view(request):
    return HttpResponse("Settings Page")


@login_required
def workflow_guide_view(request):
    return render(request, WORKFLOW_GUIDE_TEMPLATE)


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

    return render(request, PROFILE_EDIT_TEMPLATE, {"user": user})

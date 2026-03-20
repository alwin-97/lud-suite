from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from core.decorators import role_required
from core.forms import ActivityForm
from core.models import Activity


DIP_YCLP_TEMPLATE = "core/dip/yclp.html"


@login_required
@role_required(allowed_roles=["mentor"])
def dip_yclp_view(request):
    form = ActivityForm()
    recent_activities = Activity.objects.filter(user=request.user).order_by("-date")[:6]
    return render(request, DIP_YCLP_TEMPLATE, {"form": form, "recent_activities": recent_activities})


@login_required
@role_required(allowed_roles=["mentor"])
def new_activity(request):
    if request.method == "GET":
        return redirect("dip_yclp")

    if request.method == "POST":
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            exists = Activity.objects.filter(
                user=request.user,
                date=form.cleaned_data["date"],
                activity=form.cleaned_data["activity"],
                duration=form.cleaned_data["duration"],
            ).exists()

            if exists:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Duplicate entry detected. You already submitted this activity.",
                    }
                )
            activity_obj = form.save(commit=False)
            activity_obj.user = request.user
            activity_obj.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Activity submitted successfully!",
                    "new_activity": {
                        "activity_name": (
                            activity_obj.other_activity
                            if activity_obj.activity == "Others"
                            else activity_obj.activity
                        ),
                        "date": activity_obj.date.strftime("%b %d, %Y"),
                        "duration": str(activity_obj.duration),
                    },
                }
            )

        errors = {field: error.get_json_data() for field, error in form.errors.items()}
        return JsonResponse(
            {
                "status": "error",
                "message": "Form validation failed. Please check the inputs.",
                "errors": errors,
            }
        )

    return JsonResponse({"status": "error", "message": "Invalid request method"})


def dip_mentee_view(request):
    return HttpResponse("DIP - Mentee Page")


def dip_home(request):
    user = request.user
    form = ActivityForm()

    if request.method == "POST":
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.user = request.user
            activity.save()
            return redirect("dashboard")

    recent_activities = Activity.objects.filter(user=user).order_by("-date")[:5]
    return render(request, DIP_YCLP_TEMPLATE, {"form": form, "recent_activities": recent_activities})

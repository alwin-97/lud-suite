from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from core.decorators import role_required
from core.forms import ActivityForm
from core.models import Activity


DIP_YCLP_TEMPLATE = "core/dip/yclp.html"


def _decimal_to_float(value):
    return float(value or 0)


def _shift_month_start(month_start, offset):
    month_index = (month_start.year * 12) + month_start.month - 1 + offset
    year, month = divmod(month_index, 12)
    return date(year, month + 1, 1)


def _activity_label(activity_key):
    return dict(Activity.ACTIVITY_CHOICES).get(activity_key, activity_key)


def dip_activity_analytics(user):
    activities = Activity.objects.filter(user=user)
    today = timezone.localdate()
    month_start = today.replace(day=1)
    window_start = _shift_month_start(month_start, -5)

    total_entries = activities.count()
    total_hours = _decimal_to_float(activities.aggregate(total=Sum("duration"))["total"])
    hours_this_month = _decimal_to_float(
        activities.filter(date__year=today.year, date__month=today.month).aggregate(total=Sum("duration"))["total"]
    )
    latest_activity = activities.order_by("-date", "-id").first()

    activity_rows = list(
        activities.values("activity")
        .annotate(total_entries=Count("id"), total_hours=Sum("duration"))
        .order_by("activity")
    )
    activity_labels = [_activity_label(row["activity"]) for row in activity_rows]
    activity_counts = [row["total_entries"] for row in activity_rows]
    activity_hours = [_decimal_to_float(row["total_hours"]) for row in activity_rows]

    monthly_rows = {
        (row["month"].date() if hasattr(row["month"], "date") else row["month"]).replace(day=1): row
        for row in activities.filter(date__gte=window_start)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total_entries=Count("id"), total_hours=Sum("duration"))
        .order_by("month")
    }
    month_labels = []
    month_counts = []
    month_hours = []
    for offset in range(6):
        current_month = _shift_month_start(window_start, offset)
        row = monthly_rows.get(current_month, {})
        month_labels.append(current_month.strftime("%b %Y"))
        month_counts.append(row.get("total_entries", 0))
        month_hours.append(_decimal_to_float(row.get("total_hours")))

    return {
        "total_entries": total_entries,
        "total_hours": round(total_hours, 2),
        "hours_this_month": round(hours_this_month, 2),
        "average_hours": round(total_hours / total_entries, 2) if total_entries else 0.0,
        "activity_type_count": len(activity_rows),
        "latest_activity_date": latest_activity.date.strftime("%b %d, %Y") if latest_activity else "No activity yet",
        "latest_activity_name": (
            latest_activity.other_activity
            if latest_activity and latest_activity.activity == "Others" and latest_activity.other_activity
            else _activity_label(latest_activity.activity)
            if latest_activity
            else ""
        ),
        "activity_breakdown": {
            "labels": activity_labels,
            "counts": activity_counts,
            "hours": activity_hours,
        },
        "monthly_trend": {
            "labels": month_labels,
            "counts": month_counts,
            "hours": month_hours,
        },
    }


@login_required
@role_required(allowed_roles=["mentor"])
def dip_yclp_view(request):
    form = ActivityForm()
    recent_activities = Activity.objects.filter(user=request.user).order_by("-date")[:6]
    context = {
        "form": form,
        "recent_activities": recent_activities,
        "analytics": dip_activity_analytics(request.user),
        "active_page": "dip",
    }
    return render(request, DIP_YCLP_TEMPLATE, context)


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
                    "analytics": dip_activity_analytics(request.user),
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
    return render(request, DIP_YCLP_TEMPLATE, {"form": form, "recent_activities": recent_activities, "active_page": "dip"})

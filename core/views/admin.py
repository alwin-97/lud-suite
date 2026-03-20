import csv
import traceback

import openpyxl
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from core.decorators import role_required
from core.forms import (
    DomainIndicatorForm,
    MentorMenteeAssignmentForm,
    MoodCategoryForm,
    RatingDomainForm,
    RatingScaleDefinitionForm,
    ReferenceContentForm,
    SessionTypeForm,
    StatusConfigForm,
    TemplateConfigForm,
)
from core.models import (
    Activity,
    CustomUser,
    DomainIndicator,
    Mentee,
    MentorMenteeAssignment,
    MoodCategory,
    RatingDomain,
    RatingScaleDefinition,
    ReferenceContent,
    SessionType,
    StatusConfig,
    TemplateConfig,
)
from core.views.common import User


ADMIN_DASHBOARD_TEMPLATE = "core/admin/dashboard.html"
ADMIN_CONFIG_HOME_TEMPLATE = "core/admin/config/home.html"
ADMIN_CONFIG_LIST_TEMPLATE = "core/admin/config/list.html"
ADMIN_CONFIG_FORM_TEMPLATE = "core/admin/config/form.html"
ADMIN_CONFIG_DELETE_TEMPLATE = "core/admin/config/delete.html"
ADMIN_USERS_MANAGE_TEMPLATE = "core/admin/users/manage.html"
ADMIN_USERS_DETAIL_TEMPLATE = "core/admin/users/detail.html"
ADMIN_ASSIGNMENTS_MENTOR_TEMPLATE = "core/admin/assignments/manage_endorser_mentors.html"
ADMIN_ASSIGNMENTS_MENTEE_TEMPLATE = "core/admin/assignments/manage_mentee_assignments.html"


CONFIG_REGISTRY = {
    "statuses": {"model": StatusConfig, "form": StatusConfigForm, "title": "Statuses"},
    "session-types": {"model": SessionType, "form": SessionTypeForm, "title": "Session Types"},
    "rating-domains": {"model": RatingDomain, "form": RatingDomainForm, "title": "Rating Domains"},
    "domain-indicators": {"model": DomainIndicator, "form": DomainIndicatorForm, "title": "Domain Indicators"},
    "rating-scale-definitions": {
        "model": RatingScaleDefinition,
        "form": RatingScaleDefinitionForm,
        "title": "Rating Scales",
    },
    "mood-categories": {"model": MoodCategory, "form": MoodCategoryForm, "title": "Mood Categories"},
    "reference-content": {"model": ReferenceContent, "form": ReferenceContentForm, "title": "Reference Content"},
    "template-configs": {"model": TemplateConfig, "form": TemplateConfigForm, "title": "Template Configs"},
}


@role_required(allowed_roles=["admin"])
def edit_user_view(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method != "POST":
        return redirect("manage_user")

    first_name = request.POST.get("first_name")
    last_name = request.POST.get("last_name")
    email = request.POST.get("email")
    phone = request.POST.get("phone")
    role = request.POST.get("role")
    password = request.POST.get("password")
    current_year = request.POST.get("current_year")

    if not (first_name and last_name and email and phone and role):
        messages.error(request, "All fields are required.")
        return redirect("manage_user")

    if User.objects.filter(email=email).exclude(id=user.id).exists():
        messages.error(request, "User with this email already exists.")
        return redirect("manage_user")

    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.username = email
    user.phone = phone
    user.role = role
    if password:
        user.set_password(password)
    user.save()

    if role == "mentee":
        mentee, created = Mentee.objects.get_or_create(
            user=user,
            defaults={"full_name": f"{first_name} {last_name}".strip(), "current_year": int(current_year) if current_year else 1},
        )
        if not created:
            mentee.full_name = f"{first_name} {last_name}".strip()
            if current_year:
                mentee.current_year = int(current_year)
            mentee.save()

    messages.success(request, "User updated successfully.")
    return redirect("manage_user")


@role_required(allowed_roles=["admin"])
def delete_user_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect("manage_user")


@role_required(allowed_roles=["admin"])
def admin_dashboard_view(request):
    total_mentors = CustomUser.objects.filter(role="mentor").count()
    total_endorsers = CustomUser.objects.filter(role="endorser").count()
    assigned_endorsers = CustomUser.objects.filter(role="endorser", mentors__isnull=False).distinct().count()
    assigned_mentors = CustomUser.objects.filter(role="mentor", assigned_endorsers__isnull=False).distinct().count()
    context = {
        "total_mentors": total_mentors,
        "total_endorsers": total_endorsers,
        "assigned_endorsers": assigned_endorsers,
        "unassigned_endorsers": total_endorsers - assigned_endorsers,
        "assigned_mentors": assigned_mentors,
        "unassigned_mentors": total_mentors - assigned_mentors,
    }
    return render(request, ADMIN_DASHBOARD_TEMPLATE, context)


@role_required(allowed_roles=["admin"])
def admin_config_home_view(request):
    config_items = [
        {"key": "statuses", "label": "Statuses"},
        {"key": "session-types", "label": "Session Types"},
        {"key": "rating-domains", "label": "Rating Domains"},
        {"key": "domain-indicators", "label": "Domain Indicators"},
        {"key": "rating-scale-definitions", "label": "Rating Scales"},
        {"key": "mood-categories", "label": "Mood Categories"},
        {"key": "reference-content", "label": "Reference Content"},
        {"key": "template-configs", "label": "Template Configs"},
    ]
    return render(request, ADMIN_CONFIG_HOME_TEMPLATE, {"config_items": config_items})


@role_required(allowed_roles=["admin"])
def admin_config_list_view(request, config_key):
    config = CONFIG_REGISTRY.get(config_key)
    if not config:
        return HttpResponse("Config not found.", status=404)

    model_class = config["model"]
    form_class = config["form"]
    title = config["title"]
    items = model_class.objects.all()

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} saved.")
            return redirect("admin_config_list", config_key=config_key)
    else:
        form = form_class()

    return render(
        request,
        ADMIN_CONFIG_LIST_TEMPLATE,
        {"items": items, "form": form, "title": title, "config_key": config_key},
    )


@role_required(allowed_roles=["admin"])
def admin_config_edit_view(request, config_key, item_id):
    config = CONFIG_REGISTRY.get(config_key)
    if not config:
        return HttpResponse("Config not found.", status=404)

    model_class = config["model"]
    form_class = config["form"]
    title = config["title"]
    item = get_object_or_404(model_class, id=item_id)

    if request.method == "POST":
        form = form_class(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} updated.")
            return redirect("admin_config_list", config_key=config_key)
    else:
        form = form_class(instance=item)

    return render(
        request,
        ADMIN_CONFIG_FORM_TEMPLATE,
        {"form": form, "title": title, "config_key": config_key, "item": item},
    )


@role_required(allowed_roles=["admin"])
def admin_config_delete_view(request, config_key, item_id):
    config = CONFIG_REGISTRY.get(config_key)
    if not config:
        return HttpResponse("Config not found.", status=404)

    model_class = config["model"]
    title = config["title"]
    item = get_object_or_404(model_class, id=item_id)

    if request.method == "POST":
        item.delete()
        messages.success(request, f"{title} deleted.")
        return redirect("admin_config_list", config_key=config_key)

    return render(
        request,
        ADMIN_CONFIG_DELETE_TEMPLATE,
        {"title": title, "config_key": config_key, "item": item},
    )


@role_required(allowed_roles=["admin"])
def manage_mentee_assignments_view(request):
    assignments = MentorMenteeAssignment.objects.select_related("mentor", "mentee").order_by("-start_date")
    if request.method == "POST":
        form = MentorMenteeAssignmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment saved.")
            return redirect("manage_mentee_assignments")
    else:
        form = MentorMenteeAssignmentForm(initial={"start_date": timezone.now().date()})

    return render(request, ADMIN_ASSIGNMENTS_MENTEE_TEMPLATE, {"assignments": assignments, "form": form})


@role_required(allowed_roles=["admin"])
def manage_user_view(request):
    users = User.objects.exclude(role="admin").order_by("id")
    return render(request, ADMIN_USERS_MANAGE_TEMPLATE, {"users": users})


@role_required(allowed_roles=["admin"])
def add_user_view(request):
    if request.method != "POST":
        return redirect("manage_user")

    first_name = request.POST.get("first_name")
    last_name = request.POST.get("last_name")
    email = request.POST.get("email")
    phone = request.POST.get("phone")
    role = request.POST.get("role")
    current_year = request.POST.get("current_year")
    password = request.POST.get("password")

    if not all([first_name, last_name, email, phone, role]):
        messages.error(request, "All fields are required.")
        return redirect("manage_user")

    if User.objects.filter(email=email).exists():
        messages.error(request, "User with this email already exists.")
        return redirect("manage_user")

    user = CustomUser.objects.create(
        username=email,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        phone=phone,
    )
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()

    if role == "mentee":
        Mentee.objects.create(user=user, full_name=f"{first_name} {last_name}".strip(), current_year=int(current_year) if current_year else 1)

    messages.success(request, "User added successfully.")
    return redirect("manage_user")


@role_required(allowed_roles=["admin"])
def view_user(request, user_id):
    viewed_user = get_object_or_404(CustomUser, id=user_id)
    activities = Activity.objects.filter(user=viewed_user).order_by("-date")
    return render(request, ADMIN_USERS_DETAIL_TEMPLATE, {"viewed_user": viewed_user, "activities": activities})


@role_required(allowed_roles=["admin"])
def export_user_activities_excel(request, user_id):
    viewed_user = get_object_or_404(CustomUser, id=user_id)
    activities = Activity.objects.filter(user=viewed_user).order_by("-date")

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Activities"
    worksheet.append(["Activity", "Duration", "Date", "Feedback", "Learnings", "Other Activity"])

    for activity in activities:
        worksheet.append([
            activity.activity,
            activity.duration,
            activity.date.strftime("%Y-%m-%d") if activity.date else "",
            activity.feedback or "",
            activity.learnings or "",
            activity.other_activity or "",
        ])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{viewed_user.username}_activities.xlsx"'
    workbook.save(response)
    return response


@role_required(allowed_roles=["admin"])
def download_user_template(request):
    response = HttpResponse(content_type="text/csv", headers={"Content-Disposition": 'attachment; filename="user_template.csv"'})
    writer = csv.writer(response)
    writer.writerow(["FIRST_NAME", "LAST_NAME", "EMAIL", "PHONENO", "ROLE"])
    return response


@role_required(allowed_roles=["admin"])
def bulk_upload_users_view(request):
    if request.method == "POST":
        csv_file = request.FILES.get("file")
        if not csv_file:
            messages.error(request, "No file uploaded.")
            return redirect("manage_user")
        if not csv_file.name.endswith(".csv"):
            messages.error(request, "Uploaded file is not a CSV.")
            return redirect("manage_user")

        try:
            decoded_file = csv_file.read().decode("utf-8").splitlines()
            reader = csv.DictReader(decoded_file)
        except Exception:
            messages.error(request, "Error reading the CSV. Ensure it is properly formatted.")
            return redirect("manage_user")

        reader = [{key.strip(): value for key, value in row.items()} for row in reader]
        required_fields = ["FIRST_NAME", "LAST_NAME", "EMAIL", "PHONENO", "ROLE"]
        added_count = 0
        skipped_rows = []

        for index, row in enumerate(reader, start=2):
            row = {key: (value or "").strip() for key, value in row.items()}
            if not all(row.get(field) for field in required_fields):
                skipped_rows.append(f"Row {index}: One or more required fields are empty.")
                continue

            first_name = row["FIRST_NAME"]
            last_name = row["LAST_NAME"]
            email = row["EMAIL"]
            phone = row["PHONENO"]
            role = row["ROLE"].lower()

            if role not in ["endorser", "mentor", "mentee", "reviewer"]:
                skipped_rows.append(
                    f"Row {index}: Invalid role '{row['ROLE']}'. Must be 'endorser', 'mentor', 'mentee', or 'reviewer'."
                )
                continue
            if CustomUser.objects.filter(email=email).exists():
                skipped_rows.append(f"Row {index}: Email '{email}' already exists.")
                continue

            username_base = f"{first_name.lower()}.{last_name.lower()}"
            username = username_base
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{username_base}{counter}"
                counter += 1

            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role,
                password="DefaultPass123",
            )
            if role == "mentee":
                Mentee.objects.create(user=user, full_name=f"{first_name} {last_name}".strip(), current_year=1)
            added_count += 1

        if added_count:
            messages.success(request, f"{added_count} users added successfully.")
        if skipped_rows:
            skipped_msg = "<br>".join(skipped_rows)
            messages.warning(request, mark_safe(f"Some rows were skipped:<br>{skipped_msg}"))

    return redirect("manage_user")


@role_required(allowed_roles=["admin"])
def manage_assignment(request):
    all_endorsers = CustomUser.objects.filter(role="endorser")
    all_mentors = CustomUser.objects.filter(role="mentor")
    unassigned_endorsers = all_endorsers.filter(mentors__isnull=True)
    unassigned_mentors = all_mentors.exclude(assigned_endorsers__isnull=False)
    endorsers_with_counts = [
        {"endorser": endorser, "mentor_count": endorser.mentors.count(), "mentors": endorser.mentors.all()}
        for endorser in all_endorsers
    ]
    context = {
        "endorsers_with_counts": endorsers_with_counts,
        "unassigned_endorsers": unassigned_endorsers,
        "unassigned_mentors": unassigned_mentors,
        "total_endorsers": all_endorsers.count(),
        "total_mentors": all_mentors.count(),
    }
    return render(request, ADMIN_ASSIGNMENTS_MENTOR_TEMPLATE, context)


@role_required(allowed_roles=["admin"])
@require_POST
def assign_mentors(request):
    try:
        endorser_id = request.POST.get("endorser_id")
        mentor_ids = request.POST.getlist("mentor_ids[]")
        if not endorser_id or not mentor_ids:
            return JsonResponse({"status": "failed", "message": "Missing data"})

        endorser = User.objects.get(id=endorser_id)
        mentors = User.objects.filter(id__in=mentor_ids)
        endorser.mentors.add(*mentors)
        return JsonResponse({"status": "success", "message": "Mentors assigned successfully"})
    except Exception as exc:
        print("Assign error:", exc)
        return JsonResponse({"status": "failed", "message": str(exc)})


@role_required(allowed_roles=["admin"])
@require_POST
def unassign_mentor(request):
    endorser_id = request.POST.get("endorser_id")
    mentor_ids = request.POST.getlist("mentor_ids[]")

    try:
        endorser = CustomUser.objects.get(id=endorser_id)
        mentors = CustomUser.objects.filter(id__in=mentor_ids)
        for mentor in mentors:
            endorser.mentors.remove(mentor)
        return JsonResponse({"status": "success"})
    except Exception as exc:
        return JsonResponse({"status": "error", "message": str(exc)})


@role_required(allowed_roles=["admin"])
def get_assigned_mentors(request):
    if request.method != "GET":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    endorser_id = request.GET.get("endorser_id")
    if not endorser_id:
        return JsonResponse({"status": "error", "message": "endorser_id missing"}, status=400)

    try:
        endorser = CustomUser.objects.get(id=endorser_id)
        mentors_qs = endorser.mentors.all().values("id", "first_name", "last_name", "email")
        return JsonResponse({"status": "success", "mentors": list(mentors_qs)})
    except CustomUser.DoesNotExist:
        return JsonResponse({"status": "error", "message": f"Endorser with id={endorser_id} not found"}, status=404)
    except Exception as exc:
        return JsonResponse({"status": "error", "message": str(exc), "trace": traceback.format_exc()}, status=500)


@role_required(allowed_roles=["admin"])
@require_POST
def update_assigned_mentors(request):
    endorser_id = request.POST.get("endorser_id")
    mentor_ids = request.POST.getlist("mentor_ids[]")

    try:
        endorser = CustomUser.objects.get(id=endorser_id)
        endorser.mentors.set(mentor_ids)
        return JsonResponse({"status": "success"})
    except Exception as exc:
        return JsonResponse({"status": "error", "message": str(exc)})

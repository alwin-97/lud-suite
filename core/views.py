from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, login, authenticate
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .forms import (
    ActivityForm,
    NotificationForm,
    ProfileForm,
    WorkScheduleForm,
    ObjectiveItemForm,
    ObjectiveItemMentorForm,
    YearPlanItemForm,
    YearPlanItemMentorForm,
    MenteeAssessmentForm,
    MentorMenteeAssignmentForm,
    StatusConfigForm,
    SessionTypeForm,
    RatingDomainForm,
    DomainIndicatorForm,
    MoodCategoryForm,
    ReferenceContentForm,
    TemplateConfigForm,
)
from .models import (
    CustomUser,
    Assignment,
    MentorProfile,
    WorkSchedule,
    Activity,
    Notification,
    Mentee,
    MentorMenteeAssignment,
    ObjectiveItem,
    YearPlanItem,
    StatusConfig,
    MenteeAssessment,
    AssessmentRating,
    RatingDomain,
    SessionType,
    DomainIndicator,
    MoodCategory,
    ReferenceContent,
    TemplateConfig,
)
from .decorators import role_required
from django.contrib import messages
import openpyxl
import csv
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST


User = get_user_model()


def _active_assignments_qs(mentor):
    today = timezone.now().date()
    return MentorMenteeAssignment.objects.filter(
        mentor=mentor,
        is_active=True,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))


def _get_mentee_for_user(user):
    return Mentee.objects.filter(user=user).first()


def _mentor_can_access_mentee(user, mentee):
    if user.is_superuser or getattr(user, "role", None) == "admin":
        return True
    return _active_assignments_qs(user).filter(mentee=mentee).exists()


def _domains_for_year(year):
    return RatingDomain.objects.filter(year=year, is_active=True).order_by("sort_order", "name")
@role_required(allowed_roles=['admin'])
def edit_user_view(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        role = request.POST.get("role")
        password = request.POST.get("password")
        current_year = request.POST.get("current_year")

        if not (first_name and last_name and email and phone and role):
            messages.error(request, "⚠️ All fields are required.")
            return redirect("edit_user", user_id=user.id)

        # update fields
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
                defaults={
                    "full_name": f"{first_name} {last_name}".strip(),
                    "current_year": int(current_year) if current_year else 1,
                },
            )
            if not created:
                mentee.full_name = f"{first_name} {last_name}".strip()
                if current_year:
                    mentee.current_year = int(current_year)
                mentee.save()

        messages.success(request, "✅ User updated successfully.")
        return redirect("manage_user")

    return render(request, "core/edit_user.html", {"user": user})


@role_required(allowed_roles=['admin'])
def delete_user_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, "🗑️ User deleted successfully.")
    return redirect("manage_user")



# -------------------- Dashboards --------------------
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not password:
            messages.error(request, "Password is required.")
            return redirect("login")

        user = authenticate(request, username=email, password=password)
        if not user:
            try:
                user_obj = CustomUser.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except CustomUser.DoesNotExist:
                user = None
        if not user:
            messages.error(request, "Invalid email or password.")
            return redirect("login")

        login(request, user)
        return redirect("role-redirect")
    return render(request, "core/login.html")


@role_required(allowed_roles=['admin'])
def admin_dashboard_view(request):
    total_mentors = CustomUser.objects.filter(role='mentor').count()
    total_endorsers = CustomUser.objects.filter(role='endorser').count()

    # Assigned/Unassigned Endorsers
    assigned_endorsers = CustomUser.objects.filter(role='endorser', mentors__isnull=False).distinct().count()
    unassigned_endorsers = total_endorsers - assigned_endorsers

    # Assigned/Unassigned Mentors
    assigned_mentors = CustomUser.objects.filter(role='mentor', assigned_endorsers__isnull=False).distinct().count()
    unassigned_mentors = total_mentors - assigned_mentors

    context = {
        'total_mentors': total_mentors,
        'total_endorsers': total_endorsers,
        'assigned_endorsers': assigned_endorsers,
        'unassigned_endorsers': unassigned_endorsers,
        'assigned_mentors': assigned_mentors,
        'unassigned_mentors': unassigned_mentors,
    }
    return render(request, "core/admin_dashboard.html", context)


@role_required(allowed_roles=['admin'])
def admin_config_home_view(request):
    config_items = [
        {"key": "statuses", "label": "Statuses"},
        {"key": "session-types", "label": "Session Types"},
        {"key": "rating-domains", "label": "Rating Domains"},
        {"key": "domain-indicators", "label": "Domain Indicators"},
        {"key": "mood-categories", "label": "Mood Categories"},
        {"key": "reference-content", "label": "Reference Content"},
        {"key": "template-configs", "label": "Template Configs"},
    ]
    return render(request, "core/admin_config_home.html", {"config_items": config_items})


CONFIG_REGISTRY = {
    "statuses": {
        "model": StatusConfig,
        "form": StatusConfigForm,
        "title": "Statuses",
    },
    "session-types": {
        "model": SessionType,
        "form": SessionTypeForm,
        "title": "Session Types",
    },
    "rating-domains": {
        "model": RatingDomain,
        "form": RatingDomainForm,
        "title": "Rating Domains",
    },
    "domain-indicators": {
        "model": DomainIndicator,
        "form": DomainIndicatorForm,
        "title": "Domain Indicators",
    },
    "mood-categories": {
        "model": MoodCategory,
        "form": MoodCategoryForm,
        "title": "Mood Categories",
    },
    "reference-content": {
        "model": ReferenceContent,
        "form": ReferenceContentForm,
        "title": "Reference Content",
    },
    "template-configs": {
        "model": TemplateConfig,
        "form": TemplateConfigForm,
        "title": "Template Configs",
    },
}


@role_required(allowed_roles=['admin'])
def admin_config_list_view(request, config_key):
    config = CONFIG_REGISTRY.get(config_key)
    if not config:
        return HttpResponse("Config not found.", status=404)

    Model = config["model"]
    Form = config["form"]
    title = config["title"]
    items = Model.objects.all()

    if request.method == "POST":
        form = Form(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} saved.")
            return redirect("admin_config_list", config_key=config_key)
    else:
        form = Form()

    return render(
        request,
        "core/admin_config_list.html",
        {"items": items, "form": form, "title": title, "config_key": config_key},
    )


@role_required(allowed_roles=['admin'])
def admin_config_edit_view(request, config_key, item_id):
    config = CONFIG_REGISTRY.get(config_key)
    if not config:
        return HttpResponse("Config not found.", status=404)

    Model = config["model"]
    Form = config["form"]
    title = config["title"]
    item = get_object_or_404(Model, id=item_id)

    if request.method == "POST":
        form = Form(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} updated.")
            return redirect("admin_config_list", config_key=config_key)
    else:
        form = Form(instance=item)

    return render(
        request,
        "core/admin_config_form.html",
        {"form": form, "title": title, "config_key": config_key, "item": item},
    )


@role_required(allowed_roles=['admin'])
def admin_config_delete_view(request, config_key, item_id):
    config = CONFIG_REGISTRY.get(config_key)
    if not config:
        return HttpResponse("Config not found.", status=404)

    Model = config["model"]
    title = config["title"]
    item = get_object_or_404(Model, id=item_id)

    if request.method == "POST":
        item.delete()
        messages.success(request, f"{title} deleted.")
        return redirect("admin_config_list", config_key=config_key)

    return render(
        request,
        "core/admin_config_delete.html",
        {"title": title, "config_key": config_key, "item": item},
    )


@role_required(allowed_roles=['admin'])
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

    return render(
        request,
        "core/manage_mentee_assignments.html",
        {"assignments": assignments, "form": form},
    )



@role_required(allowed_roles=['endorser'])
def endorser_dashboard(request):
    return render(request, 'core/endorser_dashboard.html')

@role_required(allowed_roles=['mentor'])
def dashboard_view(request):
    assignments = _active_assignments_qs(request.user).select_related("mentee")
    mentees = [assignment.mentee for assignment in assignments]
    context = {
        "assignments": assignments,
        "mentees": mentees,
    }
    return render(request, "core/mentor_dashboard.html", context)


@role_required(allowed_roles=['mentee'])
def mentee_dashboard_view(request):
    mentee = _get_mentee_for_user(request.user)
    if not mentee:
        messages.warning(request, "Your mentee profile is not set up yet.")
        return render(request, "core/mentee_dashboard.html", {"mentee": None})

    objectives = ObjectiveItem.objects.filter(mentee=mentee)
    year_plans = YearPlanItem.objects.filter(mentee=mentee)

    objective_status_counts = (
        objectives.values("status__name")
        .annotate(count=Count("id"))
        .order_by("status__name")
    )
    year_plan_counts = (
        year_plans.values("year")
        .annotate(count=Count("id"))
        .order_by("year")
    )

    context = {
        "mentee": mentee,
        "objectives": objectives[:5],
        "year_plans": year_plans[:5],
        "objective_status_counts": objective_status_counts,
        "year_plan_counts": year_plan_counts,
    }
    return render(request, "core/mentee_dashboard.html", context)


# -------------------- Authentication Redirect --------------------

@login_required
def role_redirect_view(request):
    user = request.user

    if user.is_superuser or user.role == "admin":
        return redirect("admin_dashboard")
    elif user.role == "mentor":
        return redirect("dashboard")
    elif user.role == "mentee":
        return redirect("mentee_dashboard")
    elif user.role == "endorser":
        return redirect("endorser_dashboard")
    elif user.role == "reviewer":
        return redirect("mentor_mentee_list")
    else:
        # Fallback if role not set
        return redirect("profile")


# -------------------- DIP Objective / Year Plan Tracking --------------------
@login_required
@role_required(allowed_roles=['mentee'])
def objective_list_view(request):
    mentee = _get_mentee_for_user(request.user)
    if not mentee:
        messages.warning(request, "Your mentee profile is not set up yet.")
        return render(request, "core/objective_list.html", {"mentee": None})
    objectives = ObjectiveItem.objects.filter(mentee=mentee).select_related("status")
    return render(request, "core/objective_list.html", {"mentee": mentee, "objectives": objectives})


@login_required
@role_required(allowed_roles=['mentee'])
def objective_create_view(request):
    mentee = _get_mentee_for_user(request.user)
    if not mentee:
        messages.warning(request, "Your mentee profile is not set up yet.")
        return redirect("mentee_dashboard")
    if request.method == "POST":
        form = ObjectiveItemForm(request.POST, request.FILES)
        if form.is_valid():
            objective = form.save(commit=False)
            objective.mentee = mentee
            objective.created_by = request.user
            objective.updated_by = request.user
            objective.save()
            messages.success(request, "Objective saved.")
            return redirect("objective_list")
    else:
        form = ObjectiveItemForm()
    return render(request, "core/objective_form.html", {"form": form, "mode": "create"})


@login_required
@role_required(allowed_roles=['mentee'])
def objective_edit_view(request, objective_id):
    mentee = _get_mentee_for_user(request.user)
    if not mentee:
        messages.warning(request, "Your mentee profile is not set up yet.")
        return redirect("mentee_dashboard")
    objective = get_object_or_404(ObjectiveItem, id=objective_id, mentee=mentee)
    if request.method == "POST":
        form = ObjectiveItemForm(request.POST, request.FILES, instance=objective)
        if form.is_valid():
            objective = form.save(commit=False)
            objective.updated_by = request.user
            objective.save()
            messages.success(request, "Objective updated.")
            return redirect("objective_list")
    else:
        form = ObjectiveItemForm(instance=objective)
    return render(request, "core/objective_form.html", {"form": form, "mode": "edit", "objective": objective})


@login_required
@role_required(allowed_roles=['mentor', 'reviewer', 'admin'])
def mentor_mentee_list_view(request):
    if request.user.role == "mentor":
        mentees = Mentee.objects.filter(
            mentor_assignments__in=_active_assignments_qs(request.user)
        ).distinct()
    else:
        mentees = Mentee.objects.all()
    return render(request, "core/mentor_mentee_list.html", {"mentees": mentees})


@login_required
@role_required(allowed_roles=['mentor', 'reviewer', 'admin'])
def mentor_objective_list_view(request, mentee_id):
    mentee = get_object_or_404(Mentee, id=mentee_id)
    if request.user.role in ["mentor"] and not _mentor_can_access_mentee(request.user, mentee):
        return HttpResponse("You are not allowed to access this mentee.", status=403)
    objectives = ObjectiveItem.objects.filter(mentee=mentee).select_related("status")
    return render(request, "core/mentor_objective_list.html", {"mentee": mentee, "objectives": objectives})


@login_required
@role_required(allowed_roles=['mentor', 'admin'])
def mentor_objective_update_view(request, objective_id):
    objective = get_object_or_404(ObjectiveItem, id=objective_id)
    if request.user.role == "mentor" and not _mentor_can_access_mentee(request.user, objective.mentee):
        return HttpResponse("You are not allowed to access this mentee.", status=403)
    if request.method == "POST":
        form = ObjectiveItemMentorForm(request.POST, instance=objective)
        if form.is_valid():
            objective = form.save(commit=False)
            objective.updated_by = request.user
            if objective.mentor_approved and objective.approved_at is None:
                objective.approved_at = timezone.now()
            objective.save()
            messages.success(request, "Mentor feedback saved.")
            return redirect("mentor_objective_list", mentee_id=objective.mentee_id)
    else:
        form = ObjectiveItemMentorForm(instance=objective)
    return render(
        request,
        "core/mentor_objective_form.html",
        {"form": form, "objective": objective},
    )


@login_required
@role_required(allowed_roles=['mentee'])
def year_plan_list_view(request):
    mentee = _get_mentee_for_user(request.user)
    if not mentee:
        messages.warning(request, "Your mentee profile is not set up yet.")
        return render(request, "core/year_plan_list.html", {"mentee": None})
    year_plans = YearPlanItem.objects.filter(mentee=mentee).select_related("status")
    return render(request, "core/year_plan_list.html", {"mentee": mentee, "year_plans": year_plans})


@login_required
@role_required(allowed_roles=['mentee'])
def year_plan_create_view(request):
    mentee = _get_mentee_for_user(request.user)
    if not mentee:
        messages.warning(request, "Your mentee profile is not set up yet.")
        return redirect("mentee_dashboard")
    if request.method == "POST":
        form = YearPlanItemForm(request.POST)
        if form.is_valid():
            year_plan = form.save(commit=False)
            year_plan.mentee = mentee
            year_plan.created_by = request.user
            year_plan.updated_by = request.user
            year_plan.save()
            messages.success(request, "Year plan saved.")
            return redirect("year_plan_list")
    else:
        form = YearPlanItemForm()
    return render(request, "core/year_plan_form.html", {"form": form, "mode": "create"})


@login_required
@role_required(allowed_roles=['mentee'])
def year_plan_edit_view(request, year_plan_id):
    mentee = _get_mentee_for_user(request.user)
    if not mentee:
        messages.warning(request, "Your mentee profile is not set up yet.")
        return redirect("mentee_dashboard")
    year_plan = get_object_or_404(YearPlanItem, id=year_plan_id, mentee=mentee)
    if request.method == "POST":
        form = YearPlanItemForm(request.POST, instance=year_plan)
        if form.is_valid():
            year_plan = form.save(commit=False)
            year_plan.updated_by = request.user
            year_plan.save()
            messages.success(request, "Year plan updated.")
            return redirect("year_plan_list")
    else:
        form = YearPlanItemForm(instance=year_plan)
    return render(request, "core/year_plan_form.html", {"form": form, "mode": "edit", "year_plan": year_plan})


@login_required
@role_required(allowed_roles=['mentor', 'reviewer', 'admin'])
def mentor_year_plan_list_view(request, mentee_id):
    mentee = get_object_or_404(Mentee, id=mentee_id)
    if request.user.role == "mentor" and not _mentor_can_access_mentee(request.user, mentee):
        return HttpResponse("You are not allowed to access this mentee.", status=403)
    year_plans = YearPlanItem.objects.filter(mentee=mentee).select_related("status")
    return render(request, "core/mentor_year_plan_list.html", {"mentee": mentee, "year_plans": year_plans})


@login_required
@role_required(allowed_roles=['mentor', 'admin'])
def mentor_year_plan_update_view(request, year_plan_id):
    year_plan = get_object_or_404(YearPlanItem, id=year_plan_id)
    if request.user.role == "mentor" and not _mentor_can_access_mentee(request.user, year_plan.mentee):
        return HttpResponse("You are not allowed to access this mentee.", status=403)
    if request.method == "POST":
        form = YearPlanItemMentorForm(request.POST, instance=year_plan)
        if form.is_valid():
            year_plan = form.save(commit=False)
            year_plan.updated_by = request.user
            year_plan.save()
            messages.success(request, "Mentor feedback saved.")
            return redirect("mentor_year_plan_list", mentee_id=year_plan.mentee_id)
    else:
        form = YearPlanItemMentorForm(instance=year_plan)
    return render(
        request,
        "core/mentor_year_plan_form.html",
        {"form": form, "year_plan": year_plan},
    )


@login_required
@role_required(allowed_roles=['mentee'])
def mentee_assessment_list_view(request):
    mentee = _get_mentee_for_user(request.user)
    if not mentee:
        messages.warning(request, "Your mentee profile is not set up yet.")
        return render(request, "core/mentee_assessment_list.html", {"mentee": None})
    assessments = MenteeAssessment.objects.filter(mentee=mentee).select_related("session_type")
    return render(
        request,
        "core/mentee_assessment_list.html",
        {"mentee": mentee, "assessments": assessments},
    )


@login_required
@role_required(allowed_roles=['mentor', 'reviewer', 'admin'])
def mentor_assessment_list_view(request, mentee_id):
    mentee = get_object_or_404(Mentee, id=mentee_id)
    if request.user.role == "mentor" and not _mentor_can_access_mentee(request.user, mentee):
        return HttpResponse("You are not allowed to access this mentee.", status=403)
    assessments = MenteeAssessment.objects.filter(mentee=mentee).select_related("session_type")
    return render(
        request,
        "core/mentor_assessment_list.html",
        {"mentee": mentee, "assessments": assessments},
    )


@login_required
@role_required(allowed_roles=['mentor', 'admin'])
def mentor_assessment_create_view(request, mentee_id):
    mentee = get_object_or_404(Mentee, id=mentee_id)
    if request.user.role == "mentor" and not _mentor_can_access_mentee(request.user, mentee):
        return HttpResponse("You are not allowed to access this mentee.", status=403)

    rating_errors = []
    if request.method == "POST":
        form = MenteeAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.mentee = mentee
            assessment.mentor = request.user
            assessment.save()

            domains = _domains_for_year(assessment.year)
            for domain in domains:
                value = request.POST.get(f"rating_{domain.id}")
                if value:
                    AssessmentRating.objects.update_or_create(
                        assessment=assessment,
                        domain=domain,
                        defaults={"value": int(value)},
                    )
                else:
                    rating_errors.append(domain.name)

            if rating_errors:
                assessment.delete()
                messages.error(request, "Please provide ratings for all domains.")
            else:
                messages.success(request, "Assessment saved.")
                return redirect("mentor_assessment_list", mentee_id=mentee.id)
    else:
        form = MenteeAssessmentForm(initial={"year": mentee.current_year})

    year_value = form.data.get("year") or form.initial.get("year") or mentee.current_year
    domains = _domains_for_year(year_value)

    return render(
        request,
        "core/mentor_assessment_form.html",
        {
            "mentee": mentee,
            "form": form,
            "domains": domains,
            "rating_errors": rating_errors,
        },
    )


@login_required
def export_mentee_progress_csv(request, mentee_id):
    mentee = get_object_or_404(Mentee, id=mentee_id)
    if request.user.role == "mentee" and mentee.user_id != request.user.id:
        return HttpResponse("You are not allowed to export this mentee.", status=403)
    if request.user.role == "mentor" and not _mentor_can_access_mentee(request.user, mentee):
        return HttpResponse("You are not allowed to export this mentee.", status=403)

    objectives = ObjectiveItem.objects.filter(mentee=mentee).select_related("status")
    year_plans = YearPlanItem.objects.filter(mentee=mentee).select_related("status")
    assessments = MenteeAssessment.objects.filter(mentee=mentee).select_related("session_type")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{mentee.id}_progress.csv"'
    writer = csv.writer(response)

    writer.writerow(["Objectives"])
    writer.writerow([
        "Title",
        "Objective Text",
        "Action Items",
        "Start Date",
        "End Date",
        "Expected Outcome",
        "Status",
        "Progress %",
        "Mentee Remarks",
        "Mentor Comments",
    ])
    for obj in objectives:
        writer.writerow([
            obj.objective_title,
            obj.objective_text,
            obj.action_items,
            obj.start_date,
            obj.end_date,
            obj.expected_outcome,
            obj.status.name if obj.status else "",
            obj.progress_percent,
            obj.mentee_remarks,
            obj.mentor_comments,
        ])

    writer.writerow([])
    writer.writerow(["Year Plans"])
    writer.writerow([
        "Year",
        "Milestone",
        "Deliverable",
        "Target Date",
        "Target Period",
        "Status",
        "Remarks",
        "Mentor Comments",
        "Review Date",
    ])
    for plan in year_plans:
        writer.writerow([
            plan.get_year_display(),
            plan.milestone,
            plan.deliverable,
            plan.target_date,
            plan.target_period,
            plan.status.name if plan.status else "",
            plan.remarks,
            plan.mentor_comments,
            plan.review_date,
        ])

    writer.writerow([])
    writer.writerow(["Assessments"])
    writer.writerow([
        "Date",
        "Year",
        "Session Type",
        "Theme/Topic",
        "Beginning Mood",
        "End Mood",
        "Average",
        "Mentor Remarks",
        "Action Plan",
    ])
    for assessment in assessments:
        writer.writerow([
            assessment.date,
            assessment.get_year_display(),
            assessment.session_type,
            assessment.theme_topic,
            assessment.beginning_mood,
            assessment.end_mood,
            assessment.average_score(),
            assessment.mentor_remarks,
            assessment.action_plan,
        ])

    return response



# -------------------- Core Pages (mentee-related) --------------------

@login_required
@role_required(allowed_roles=['mentor'])
def dip_yclp_view(request):
    form = ActivityForm()   # <-- ADD THIS
    recent_activities = Activity.objects.filter(user=request.user).order_by("-date")[:6]

    return render(request, "core/dip_yclp.html", {
        "form": form,
        "recent_activities": recent_activities
    })

@login_required
@csrf_exempt  # only needed if CSRF issues persist, ideally handle via headers in AJAX
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
                duration=form.cleaned_data["duration"]
            ).exists()

            if exists:
                return JsonResponse({
                    "status": "error",
                    "message": "Duplicate entry detected. You already submitted this activity."
                })
            activity_obj = form.save(commit=False)
            activity_obj.user = request.user
            activity_obj.save()
            
            return JsonResponse({
                "status": "success",
                "message": "Activity submitted successfully!",
                "new_activity": {
                    "activity_name": activity_obj.other_activity if activity_obj.activity == "Others" else activity_obj.activity,
                    "date": activity_obj.date.strftime("%b %d, %Y"),
                    "duration": str(activity_obj.duration)
                }
            })
        else:
            # Send form errors back
            errors = {field: error.get_json_data() for field, error in form.errors.items()}
            return JsonResponse({
                "status": "error",
                "message": "Form validation failed. Please check the inputs.",
                "errors": errors
            })
    return JsonResponse({"status": "error", "message": "Invalid request method"})



@login_required
@role_required(allowed_roles=['mentor'])
def my_activities_view(request):
    # Fetch all activities of the logged-in mentor
    activities = Activity.objects.filter(user=request.user).order_by('-date')

    return render(request, 'core/my_activities.html', {
        'activities': activities
    })




# -------------------- Other Placeholder Pages --------------------

def dip_mentee_view(request):
    return HttpResponse("DIP - Mentee Page")
@login_required
def profile_view(request):
    return render(request, "core/profile.html", {"user": request.user})
@login_required
def profile_edit(request):
    user = request.user
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = ProfileUpdateForm(instance=user)
    return render(request, "core/profile_edit.html", {"form": form})

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
    return render(request, "core/workflow_guide.html")

@role_required(allowed_roles=["admin"])
def manage_user_view(request):
    users = User.objects.exclude(role='admin').order_by("id")  # fetch all users
    return render(request, "core/manage_user.html", {"users": users})

User = get_user_model()
User = get_user_model()

@role_required(allowed_roles=["admin"])
def add_user_view(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        role = request.POST.get("role")
        current_year = request.POST.get("current_year")
        password = request.POST.get("password")

        if not all([first_name, last_name, email, phone, role]):
            messages.error(request, "All fields are required.")
            return redirect("add_user")

        if User.objects.filter(email=email).exists():
            messages.error(request, "User with this email already exists.")
            return redirect("add_user")

        user = CustomUser.objects.create(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            phone=phone
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()

        if role == "mentee":
            Mentee.objects.create(
                user=user,
                full_name=f"{first_name} {last_name}".strip(),
                current_year=int(current_year) if current_year else 1,
            )

        messages.success(request, "User added successfully.")
        return redirect("manage_user")

    return render(request, "core/add_user.html")
@login_required
def manage_user(request):
    role_filter = request.GET.get('role')
    if role_filter:
        users = User.objects.filter(role__iexact=role_filter)
    else:
        users = User.objects.all()
    return render(request, 'manage-user.html', {'users': users})
# views.py
def dashboard(request):
    total_mentors = Mentor.objects.count()
    total_endorsers = Endorser.objects.count()
    unassigned_endorsers = Endorser.objects.filter(assigned_mentor__isnull=True).count()
    assigned_endorsers = total_endorsers - unassigned_endorsers

    context = {
        'total_mentors': total_mentors,
        'total_endorsers': total_endorsers,
        'assigned_endorsers': assigned_endorsers,
        'unassigned_endorsers': unassigned_endorsers,
    }
    return render(request, 'dashboard.html', context)
@role_required(allowed_roles=["admin"])
def view_user(request, user_id):
    viewed_user = get_object_or_404(CustomUser, id=user_id)
    activities = Activity.objects.filter(user=viewed_user).order_by('-date')
    return render(request, 'core/view_user.html', {
        'viewed_user': viewed_user,
        'activities': activities
    })
def export_user_activities_excel(request, user_id):
    viewed_user = get_object_or_404(CustomUser, id=user_id)
    activities = Activity.objects.filter(user=viewed_user).order_by('-date')

    # Create workbook and sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Activities"

    # Header row
    ws.append(["Activity", "Duration", "Date", "Feedback", "Learnings", "Other Activity"])

    # Data rows
    for activity in activities:
        ws.append([
            activity.activity,
            activity.duration,
            activity.date.strftime("%Y-%m-%d") if activity.date else "",
            activity.feedback or "",
            activity.learnings or "",
            activity.other_activity or "",
        ])

    # Response with Excel file
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    filename = f"{viewed_user.username}_activities.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response

@login_required
def profile_edit(request):
    user = request.user

    if request.method == 'POST':
        # Example: saving fields
        user.gender = request.POST.get('gender')
        user.date_of_birth = request.POST.get('date_of_birth') or None
        user.religion = request.POST.get('religion')
        user.phone_number = request.POST.get('phone_number')
        user.permanent_address = request.POST.get('permanent_address')
        user.institution = request.POST.get('institution')
        user.designation = request.POST.get('designation')
        profile_pic = request.FILES.get('profile_pic')
        if profile_pic:
            user.profile_pic = profile_pic
        user.save()
        if request.FILES.get('profile_pic'):
            user.profile_pic = request.FILES['profile_pic']

        user.save()
        return redirect('profile')  # redirect back to profile view

    return render(request, 'core/profile_edit.html', {'user': user})

@login_required
@role_required(allowed_roles=['endorser'])
def endorser_work_schedule(request):
    endorser = request.user  # The logged-in endorser

    if endorser.role != 'endorser':
        messages.error(request, "You do not have permission to access this page.")
        return redirect('endorser_dashboard')

    if request.method == 'POST':
        form = WorkScheduleForm(request.POST, endorser=endorser)
        if form.is_valid():
            work_schedule = form.save(commit=False)
            work_schedule.endorser = endorser
            work_schedule.save()
            form.save_m2m()  # Save many-to-many mentors

            # (Optional) You can loop and create notifications for each mentor here
            for mentor in form.cleaned_data['mentors']:
                Notification.objects.create(
                    message=f"New work schedule: {work_schedule.role} (Due {work_schedule.due_date})",
                    target_group='mentor',
                    created_by=endorser
                 )

            messages.success(request, "Work schedule sent successfully.",extra_tags='work_schedule')
            return redirect('endorser_work_schedule')
    else:
        form = WorkScheduleForm(endorser=request.user)

    return render(request, 'core/work_schedule.html', {'form': form})

@login_required
@role_required(allowed_roles=['endorser'])
def endorser_profile(request):
    if request.user.role != 'endorser':
        return redirect('role-redirect')
    return render(request, 'core/endorser_profile.html')

@login_required
@role_required(allowed_roles=['endorser'])
def endorser_edit_profile(request):
    if request.user.role != 'endorser':
        return redirect('role-redirect')

    user = request.user

    if request.method == 'POST':
        user.gender = request.POST.get('gender', user.gender)
        user.date_of_birth = request.POST.get('date_of_birth') or user.date_of_birth
        user.religion = request.POST.get('religion', user.religion)
        user.permanent_address = request.POST.get('permanent_address', user.permanent_address)
        user.institution = request.POST.get('institution', user.institution)
        user.designation = request.POST.get('designation', user.designation)

        if 'profile_pic' in request.FILES:
            user.profile_pic = request.FILES['profile_pic']

        # NEVER change role here
        user.save()
        return redirect('endorser_profile')

    # Always pass 'user' context
    return render(request, 'core/endorser_edit_profile.html', {'user': user})
def download_user_template(request):
    # Create the HttpResponse object with CSV header
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="user_template.csv"'},
    )

    writer = csv.writer(response)
    # Write header row
    writer.writerow(['FIRST_NAME', 'LAST_NAME', 'EMAIL', 'PHONENO', 'ROLE'])
    return response




REQUIRED_COLUMNS = ["First Name", "Last Name", "Email", "Phone Number", "Role"]
@login_required
def bulk_upload_users_view(request):
    if request.method == "POST":
        csv_file = request.FILES.get('file')
        
        # Check if file uploaded
        if not csv_file:
            messages.error(request, "⚠️ No file uploaded.")
            return redirect('manage_user')

        # Check file extension
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "⚠️ Uploaded file is not a CSV.")
            return redirect('manage_user')

        # Read CSV
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
        except Exception:
            messages.error(request, "⚠️ Error reading the CSV. Ensure it is properly formatted.")
            return redirect('manage_user')

        # Strip whitespace from header keys
        reader = [{k.strip(): v for k, v in row.items()} for row in reader]

        required_fields = ['FIRST_NAME', 'LAST_NAME', 'EMAIL', 'PHONENO', 'ROLE']
        added_count = 0
        skipped_rows = []

        for i, row in enumerate(reader, start=2):  # start=2 to match CSV row numbers
            # Strip whitespace from values
            row = {k: (v or '').strip() for k, v in row.items()}

            # Check for empty required fields
            if not all(row.get(field) for field in required_fields):
                skipped_rows.append(f"Row {i}: One or more required fields are empty.")
                continue

            first_name = row['FIRST_NAME']
            last_name = row['LAST_NAME']
            email = row['EMAIL']
            phone = row['PHONENO']
            role = row['ROLE'].lower()

            # Validate role
            if role not in ['endorser', 'mentor', 'mentee', 'reviewer']:
                skipped_rows.append(
                    f"Row {i}: Invalid role '{row['ROLE']}'. Must be 'endorser', 'mentor', 'mentee', or 'reviewer'."
                )
                continue

            # Check for duplicate email
            if CustomUser.objects.filter(email=email).exists():
                skipped_rows.append(f"Row {i}: Email '{email}' already exists.")
                continue

            # Generate unique username from first.last
            username_base = f"{first_name.lower()}.{last_name.lower()}"
            username = username_base
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{username_base}{counter}"
                counter += 1

            # Create user
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role,
                password='DefaultPass123'  # Or generate a random password
            )
            if role == "mentee":
                Mentee.objects.create(
                    user=user,
                    full_name=f"{first_name} {last_name}".strip(),
                    current_year=1,
                )
            added_count += 1

        # Success message
        if added_count:
            messages.success(request, f"✅ {added_count} users added successfully.")

        # Skipped rows message
        if skipped_rows:
            skipped_msg = "<br>".join(skipped_rows)
            messages.warning(request, mark_safe(f"⚠️ Some rows were skipped:<br>{skipped_msg}"))

    return redirect('manage_user')
@role_required(allowed_roles=['admin'])
def manage_assignment(request):
    all_endorsers = CustomUser.objects.filter(role='endorser')
    all_mentors = CustomUser.objects.filter(role='mentor')

    # Count how many are unassigned
    unassigned_endorsers = all_endorsers.filter(mentors__isnull=True)
    unassigned_mentors = all_mentors.exclude(assigned_endorsers__isnull=False)

    # Prepare mentor counts
    endorsers_with_counts = [
        {
            'endorser': e,
            'mentor_count': e.mentors.count(),
            'mentors': e.mentors.all()
        }
        for e in all_endorsers
    ]

    context = {
        'endorsers_with_counts': endorsers_with_counts,
        'unassigned_endorsers': unassigned_endorsers,
        'unassigned_mentors': unassigned_mentors,
        'total_endorsers': all_endorsers.count(),
        'total_mentors': all_mentors.count(),
    }
    return render(request, 'core/manage_assignment.html', context)


@csrf_exempt
@require_POST
def assign_mentors(request):
    try:
        endorser_id = request.POST.get('endorser_id')
        mentor_ids = request.POST.getlist('mentor_ids[]')

        if not endorser_id or not mentor_ids:
            return JsonResponse({'status': 'failed', 'message': 'Missing data'})

        endorser = User.objects.get(id=endorser_id)
        mentors = User.objects.filter(id__in=mentor_ids)

        # Add mentors to ManyToMany field
        endorser.mentors.add(*mentors)

        return JsonResponse({'status': 'success', 'message': 'Mentors assigned successfully'})

    except Exception as e:
        print("Assign error:", e)
        return JsonResponse({'status': 'failed', 'message': str(e)})



@csrf_exempt
def unassign_mentor(request):
    if request.method == 'POST':
        endorser_id = request.POST.get('endorser_id')
        mentor_ids = request.POST.getlist('mentor_ids[]')

        try:
            endorser = CustomUser.objects.get(id=endorser_id)
            mentors = CustomUser.objects.filter(id__in=mentor_ids)

            # ✅ Remove mentors from this endorser’s ManyToMany field
            for mentor in mentors:
                endorser.mentors.remove(mentor)

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'invalid method'}, status=405)

@csrf_exempt
def get_assigned_mentors(request):
    """Return mentors assigned to a given endorser (via M2M)"""
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    endorser_id = request.GET.get('endorser_id')
    if not endorser_id:
        return JsonResponse({'status': 'error', 'message': 'endorser_id missing'}, status=400)

    try:
        endorser = CustomUser.objects.get(id=endorser_id)
        mentors_qs = endorser.mentors.all().values('id', 'first_name', 'last_name', 'email')

        return JsonResponse({'status': 'success', 'mentors': list(mentors_qs)})

    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': f'Endorser with id={endorser_id} not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}, status=500)
def update_assigned_mentors(request):
    if request.method == 'POST':
        endorser_id = request.POST.get('endorser_id')
        mentor_ids = request.POST.getlist('mentor_ids[]')

        try:
            endorser = CustomUser.objects.get(id=endorser_id)
            endorser.mentors.set(mentor_ids)  # Replace all existing mentors
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid method'}, status=405)
@login_required
def activity_log(request):
    # Use the M2M relation on CustomUser instead of Assignment model
    assigned_mentors = request.user.mentors.all()

    context = {
        'assigned_mentors': assigned_mentors
    }
    return render(request, 'core/endorser_activity_log.html', context)
@login_required
def mentor_activity_list(request, mentor_id):
    mentor = get_object_or_404(User, id=mentor_id)
    activities = Activity.objects.filter(user=mentor).order_by('-date')  # assuming `user` FK in Activity

    context = {
        'mentor': mentor,
        'activities': activities,
    }
    return render(request, 'core/activity_list.html', context)
def add_remark(request):
    if request.method == "POST":
        activity_id = request.POST.get("activity_id")
        remark = request.POST.get("remark")
        activity = Activity.objects.get(id=activity_id)
        activity.remark = remark
        activity.save()
        return JsonResponse({
            "activity_id": activity_id,
            "remark": remark,
            "status": "success"
        })
    
@login_required
def mentor_profile(request):
    user = request.user

    # Only allow mentors to access this page
    if user.role != "mentor":
        return redirect("role-redirect")

    # The mentor is simply the logged-in user
    mentor = user

    return render(request, "core/mentor_profile.html", {
        "mentor": mentor
    })
def dip_home(request):
    user = request.user
    form = ActivityForm()

    if request.method == "POST":
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.user = request.user
            activity.save()
            return redirect("dashboard")  # or your DIP page URL

    recent_activities = Activity.objects.filter(user=user).order_by("-date")[:5]

    return render(request, "core/dip_yclp.html", {
        "form": form,
        "recent_activities": recent_activities,
    })

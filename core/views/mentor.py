from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.decorators import role_required
from core.forms import MenteeAssessmentForm, ObjectiveItemMentorForm, YearPlanItemMentorForm
from core.models import Activity, AssessmentRating, Mentee, MenteeAssessment, ObjectiveItem, YearPlanItem
from core.views.common import active_assignments_qs, domains_for_year, mentor_can_access_mentee


MENTOR_DASHBOARD_TEMPLATE = "core/mentor/dashboard.html"
MENTOR_MENTEES_TEMPLATE = "core/mentor/mentees.html"
MENTOR_OBJECTIVE_LIST_TEMPLATE = "core/mentor/objectives/list.html"
MENTOR_OBJECTIVE_FORM_TEMPLATE = "core/mentor/objectives/form.html"
MENTOR_YEAR_PLAN_LIST_TEMPLATE = "core/mentor/year_plans/list.html"
MENTOR_YEAR_PLAN_FORM_TEMPLATE = "core/mentor/year_plans/form.html"
MENTOR_ASSESSMENT_LIST_TEMPLATE = "core/mentor/assessments/list.html"
MENTOR_ASSESSMENT_FORM_TEMPLATE = "core/mentor/assessments/form.html"
MENTOR_ACTIVITIES_TEMPLATE = "core/mentor/activities.html"
MENTOR_PROFILE_TEMPLATE = "core/mentor/profile.html"


@role_required(allowed_roles=["mentor"])
def dashboard_view(request):
    assignments = active_assignments_qs(request.user).select_related("mentee")
    mentees = [assignment.mentee for assignment in assignments]
    return render(request, MENTOR_DASHBOARD_TEMPLATE, {"assignments": assignments, "mentees": mentees})


@login_required
@role_required(allowed_roles=["mentor", "reviewer", "admin"])
def mentor_mentee_list_view(request):
    if request.user.role == "mentor":
        mentees = Mentee.objects.filter(mentor_assignments__in=active_assignments_qs(request.user)).distinct()
    else:
        mentees = Mentee.objects.all()
    return render(request, MENTOR_MENTEES_TEMPLATE, {"mentees": mentees})


@login_required
@role_required(allowed_roles=["mentor", "reviewer", "admin"])
def mentor_objective_list_view(request, mentee_id):
    mentee = get_object_or_404(Mentee, id=mentee_id)
    if request.user.role == "mentor" and not mentor_can_access_mentee(request.user, mentee):
        return HttpResponse("You are not allowed to access this mentee.", status=403)
    objectives = ObjectiveItem.objects.filter(mentee=mentee).select_related("status")
    return render(request, MENTOR_OBJECTIVE_LIST_TEMPLATE, {"mentee": mentee, "objectives": objectives})


@login_required
@role_required(allowed_roles=["mentor", "admin"])
def mentor_objective_update_view(request, objective_id):
    objective = get_object_or_404(ObjectiveItem, id=objective_id)
    if request.user.role == "mentor" and not mentor_can_access_mentee(request.user, objective.mentee):
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
    return render(request, MENTOR_OBJECTIVE_FORM_TEMPLATE, {"form": form, "objective": objective})


@login_required
@role_required(allowed_roles=["mentor", "reviewer", "admin"])
def mentor_year_plan_list_view(request, mentee_id):
    mentee = get_object_or_404(Mentee, id=mentee_id)
    if request.user.role == "mentor" and not mentor_can_access_mentee(request.user, mentee):
        return HttpResponse("You are not allowed to access this mentee.", status=403)
    year_plans = YearPlanItem.objects.filter(mentee=mentee).select_related("status")
    return render(request, MENTOR_YEAR_PLAN_LIST_TEMPLATE, {"mentee": mentee, "year_plans": year_plans})


@login_required
@role_required(allowed_roles=["mentor", "admin"])
def mentor_year_plan_update_view(request, year_plan_id):
    year_plan = get_object_or_404(YearPlanItem, id=year_plan_id)
    if request.user.role == "mentor" and not mentor_can_access_mentee(request.user, year_plan.mentee):
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
    return render(request, MENTOR_YEAR_PLAN_FORM_TEMPLATE, {"form": form, "year_plan": year_plan})


@login_required
@role_required(allowed_roles=["mentor", "reviewer", "admin"])
def mentor_assessment_list_view(request, mentee_id):
    mentee = get_object_or_404(Mentee, id=mentee_id)
    if request.user.role == "mentor" and not mentor_can_access_mentee(request.user, mentee):
        return HttpResponse("You are not allowed to access this mentee.", status=403)
    assessments = MenteeAssessment.objects.filter(mentee=mentee).select_related("session_type")
    return render(
        request,
        MENTOR_ASSESSMENT_LIST_TEMPLATE,
        {"mentee": mentee, "assessments": assessments},
    )


@login_required
@role_required(allowed_roles=["mentor", "admin"])
def mentor_assessment_create_view(request, mentee_id):
    mentee = get_object_or_404(Mentee, id=mentee_id)
    if request.user.role == "mentor" and not mentor_can_access_mentee(request.user, mentee):
        return HttpResponse("You are not allowed to access this mentee.", status=403)

    rating_errors = []
    current_ratings = {}
    if request.method == "POST":
        form = MenteeAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.mentee = mentee
            assessment.mentor = request.user
            assessment.save()

            domains = domains_for_year(assessment.year)
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

        current_ratings = {
            key.removeprefix("rating_"): value
            for key, value in request.POST.items()
            if key.startswith("rating_")
        }
    else:
        form = MenteeAssessmentForm(initial={"year": mentee.current_year})

    year_value = form.data.get("year") or form.initial.get("year") or mentee.current_year
    domains = list(domains_for_year(year_value))
    domain_rows = [
        {"domain": domain, "selected_rating": current_ratings.get(str(domain.id), "")}
        for domain in domains
    ]

    return render(
        request,
        MENTOR_ASSESSMENT_FORM_TEMPLATE,
        {
            "mentee": mentee,
            "form": form,
            "domain_rows": domain_rows,
            "rating_errors": rating_errors,
        },
    )


@login_required
@role_required(allowed_roles=["mentor"])
def my_activities_view(request):
    activities = Activity.objects.filter(user=request.user).order_by("-date")
    return render(request, MENTOR_ACTIVITIES_TEMPLATE, {"activities": activities})


@login_required
def mentor_profile(request):
    if request.user.role != "mentor":
        return redirect("role-redirect")
    return render(request, MENTOR_PROFILE_TEMPLATE, {"mentor": request.user})

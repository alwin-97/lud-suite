from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import redirect, render

from core.models import (
    ACTIVE_MEMBERSHIP_FILTER,
    CohortMembership,
    MentorAssignment,
    QuestionResponse,
    TaskSubmission,
    Term,
    UserActivityReport,
)
from core.permissions import get_mentor_assigned_mentee_ids, get_senior_mentor_scoped_user_ids


@login_required
def workspace_home_view(request):
    if not request.user.is_authorized_user:
        logout(request)
        messages.error(request, "Your account has not been provisioned for access.")
        return redirect("login")
    if request.user.is_platform_admin:
        return redirect("admin_dashboard")

    memberships = request.user.cohort_memberships.filter(
        **ACTIVE_MEMBERSHIP_FILTER
    ).select_related(
        "cohort", "cohort__chapter", "cohort__chapter__location", "cohort__chapter__location__program"
    ).prefetch_related(
        Prefetch(
            "cohort__terms",
            queryset=Term.objects.filter(is_active=True).prefetch_related(
                "resources",
                "activities",
                "tasks",
                "tasks__submissions",
                "questions",
                "questions__responses",
            ).order_by("sequence", "start_date"),
        )
    )

    reports = list(
        request.user.activity_reports.select_related("cohort", "term", "activity").order_by("-report_date", "-created_at")
    )

    user_roles = set(m.role for m in memberships)
    is_mentor = CohortMembership.MENTOR in user_roles
    is_senior_mentor = CohortMembership.SENIOR_MEMBER in user_roles
    active_cohort_ids = [m.cohort_id for m in memberships]

    mentor_mentees = []
    if is_mentor:
        assigned_ids = get_mentor_assigned_mentee_ids(request.user)
        mentor_mentees = list(
            CohortMembership.objects.filter(
                cohort_id__in=active_cohort_ids,
                user_id__in=assigned_ids,
                is_active=True,
            ).select_related("user", "cohort").prefetch_related(
                Prefetch(
                    "user__activity_reports",
                    queryset=UserActivityReport.objects.filter(cohort_id__in=active_cohort_ids).order_by("-report_date", "-created_at"),
                ),
                Prefetch(
                    "user__task_submissions",
                    queryset=TaskSubmission.objects.filter(task__term__cohort_id__in=active_cohort_ids).select_related("task"),
                ),
                Prefetch(
                    "user__question_responses",
                    queryset=QuestionResponse.objects.filter(question__term__cohort_id__in=active_cohort_ids).select_related("question"),
                ),
            )
        )

    senior_mentorship = None
    if is_senior_mentor:
        scoped_user_ids = get_senior_mentor_scoped_user_ids(request.user)
        scoped_members = list(
            CohortMembership.objects.filter(
                cohort_id__in=active_cohort_ids,
                user_id__in=scoped_user_ids,
                is_active=True,
            ).select_related("user", "cohort").prefetch_related(
                Prefetch(
                    "user__activity_reports",
                    queryset=UserActivityReport.objects.filter(cohort_id__in=active_cohort_ids).order_by("-report_date", "-created_at"),
                ),
                Prefetch(
                    "user__task_submissions",
                    queryset=TaskSubmission.objects.filter(task__term__cohort_id__in=active_cohort_ids).select_related("task"),
                ),
                Prefetch(
                    "user__question_responses",
                    queryset=QuestionResponse.objects.filter(question__term__cohort_id__in=active_cohort_ids).select_related("question"),
                ),
            )
        )
        scoped_mentors = [m for m in scoped_members if m.role == CohortMembership.MENTOR]
        scoped_mentees = [m for m in scoped_members if m.role == CohortMembership.MENTEE]
        scoped_pairings = list(
            MentorAssignment.objects.filter(
                cohort_id__in=active_cohort_ids,
                is_active=True,
            ).select_related("mentor", "mentee", "cohort")
        )
        senior_mentorship = {
            "mentors": scoped_mentors,
            "mentees": scoped_mentees,
            "pairings": scoped_pairings,
        }

    return render(
        request,
        "core/workspace/dashboard.html",
        {
            "memberships": memberships,
            "reports": reports,
            "is_mentor": is_mentor,
            "mentor_mentees": mentor_mentees,
            "is_senior_mentor": is_senior_mentor,
            "senior_mentorship": senior_mentorship,
        },
    )

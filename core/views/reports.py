from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from core.forms import UserActivityReportForm, UserActivityReportReviewForm
from core.models import (
    ChangeHistory,
    Cohort,
    CohortActivity,
    CohortMembership,
    CustomUser,
    UserActivityReport,
    log_change,
)
from core.permissions import can_manage_user_activity_report, has_role_permission


class UserActivityReportDetailView(DetailView):
    """Comprehensive activity dossier and evaluation report for a specific participant."""

    model = CustomUser
    pk_url_kwarg = "user_id"
    template_name = "core/admin/users/activity_report.html"
    context_object_name = "target_user"

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(CustomUser, pk=kwargs["user_id"])
        if not can_manage_user_activity_report(request.user, self.target_user, action="read"):
            raise PermissionDenied("You do not have permission to view activity reports for this user.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return self.target_user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.target_user

        # Memberships
        memberships = list(
            user.cohort_memberships.filter(is_active=True).select_related(
                "cohort",
                "cohort__chapter",
                "cohort__chapter__location",
                "cohort__chapter__location__program",
            )
        )
        cohorts = [m.cohort for m in memberships]
        user_roles = {m.role for m in memberships}

        # Filtering parameters
        selected_cohort_id = self.request.GET.get("cohort", "").strip()
        selected_term_id = self.request.GET.get("term", "").strip()
        selected_status = self.request.GET.get("status", "").strip()

        # Target cohort activities relevant to user's assigned cohorts & roles
        activity_filter = Q(cohort__in=cohorts)
        audience_q = Q(target_audience=CohortActivity.TargetAudience.ALL)
        if CohortMembership.SENIOR_MEMBER in user_roles:
            audience_q |= Q(target_audience=CohortActivity.TargetAudience.SENIOR_MEMBERS)
        if CohortMembership.MENTOR in user_roles:
            audience_q |= Q(target_audience=CohortActivity.TargetAudience.MENTORS)
        if CohortMembership.MENTEE in user_roles:
            audience_q |= Q(target_audience=CohortActivity.TargetAudience.MENTEES)
        if CohortMembership.COMMUNITY_LEADER in user_roles:
            audience_q |= Q(target_audience=CohortActivity.TargetAudience.COMMUNITY_LEADERS)
        activity_filter &= audience_q

        if selected_cohort_id:
            activity_filter &= Q(cohort_id=selected_cohort_id)
        if selected_term_id:
            activity_filter &= Q(term_id=selected_term_id)

        targeted_activities = list(
            CohortActivity.objects.filter(activity_filter)
            .select_related("cohort", "term")
            .order_by("cohort__name", "term__sequence", "sequence", "start_date")
        )

        # Submitted / Prepared user activity reports
        report_filter = Q(user=user)
        if selected_cohort_id:
            report_filter &= Q(cohort_id=selected_cohort_id)
        if selected_term_id:
            report_filter &= Q(term_id=selected_term_id)
        if selected_status:
            report_filter &= Q(status=selected_status)

        reports = list(
            UserActivityReport.objects.filter(report_filter)
            .select_related("cohort", "term", "activity", "reviewed_by")
            .order_by("-report_date", "-created_at")
        )

        # Contribution audit trail
        audit_trail = list(
            ChangeHistory.objects.filter(actor=user).select_related("cohort").order_by("-created_at")[:25]
        )

        # Statistics & KPI metrics
        total_targeted = len(targeted_activities)
        completed_activities = sum(1 for a in targeted_activities if a.status == CohortActivity.Status.COMPLETED)
        in_progress_activities = sum(1 for a in targeted_activities if a.status == CohortActivity.Status.IN_PROGRESS)
        planned_activities = sum(1 for a in targeted_activities if a.status == CohortActivity.Status.PLANNED)

        total_reports = len(reports)
        approved_reports = sum(1 for r in reports if r.status == UserActivityReport.Status.APPROVED)
        submitted_reports = sum(1 for r in reports if r.status == UserActivityReport.Status.SUBMITTED)
        reviewed_reports = sum(1 for r in reports if r.status == UserActivityReport.Status.REVIEWED)
        draft_reports = sum(1 for r in reports if r.status == UserActivityReport.Status.DRAFT)

        total_hours = sum(r.hours_spent for r in reports) if reports else Decimal("0.0")

        can_create = can_manage_user_activity_report(self.request.user, user, action="create")
        can_review = (
            self.request.user.is_platform_admin
            or any(
                has_role_permission(self.request.user, "reports", "update", cohort=c)
                for c in cohorts
            )
        ) and self.request.user.pk != user.pk

        context.update(
            memberships=memberships,
            cohorts=cohorts,
            user_roles=user_roles,
            targeted_activities=targeted_activities,
            reports=reports,
            audit_trail=audit_trail,
            total_targeted=total_targeted,
            completed_activities=completed_activities,
            in_progress_activities=in_progress_activities,
            planned_activities=planned_activities,
            completion_rate=round((completed_activities / total_targeted * 100)) if total_targeted else 0,
            total_reports=total_reports,
            approved_reports=approved_reports,
            submitted_reports=submitted_reports,
            reviewed_reports=reviewed_reports,
            draft_reports=draft_reports,
            total_hours=total_hours,
            selected_cohort=selected_cohort_id,
            selected_term=selected_term_id,
            selected_status=selected_status,
            can_create=can_create,
            can_review=can_review,
        )
        return context


class UserActivityReportCreateView(CreateView):
    """Prepare and submit a new activity report for a participant."""

    model = UserActivityReport
    form_class = UserActivityReportForm
    template_name = "core/admin/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(CustomUser, pk=kwargs["user_id"])
        if not can_manage_user_activity_report(request.user, self.target_user, action="create"):
            raise PermissionDenied("You do not have permission to prepare an activity report for this user.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["target_user"] = self.target_user
        kwargs["is_reviewer"] = self.request.user.is_platform_admin or self.request.user.pk != self.target_user.pk
        cohort_id = self.request.GET.get("cohort")
        if cohort_id:
            kwargs["fixed_cohort"] = Cohort.objects.filter(pk=cohort_id).first()
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        cohort_id = self.request.GET.get("cohort")
        term_id = self.request.GET.get("term")
        activity_id = self.request.GET.get("activity")
        if cohort_id:
            initial["cohort"] = cohort_id
        if term_id:
            initial["term"] = term_id
        if activity_id:
            initial["activity"] = activity_id
            act = CohortActivity.objects.filter(pk=activity_id).first()
            if act:
                initial["title"] = f"Activity Report: {act.title}"
                initial["term"] = act.term_id
                initial["cohort"] = act.cohort_id
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.CREATE,
            entity_type="Report",
            entity_name=self.object.title,
            entity_id=self.object.pk,
            cohort=self.object.cohort,
            description=f"Prepared activity report '{self.object.title}' for {self.target_user} ({self.object.hours_spent} hrs, Status: {self.object.get_status_display()}).",
            details={
                "user": self.target_user.email,
                "cohort": self.object.cohort.name,
                "term": self.object.term.name if self.object.term else None,
                "hours_spent": str(self.object.hours_spent),
                "status": self.object.status,
            },
        )
        messages.success(self.request, f"Activity report '{self.object.title}' saved successfully.")
        return response

    def get_success_url(self):
        if self.request.user.pk == self.target_user.pk and not self.request.user.is_platform_admin:
            return reverse("workspace_reports")
        return reverse("user_activity_report", args=[self.target_user.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cancel_url = reverse("user_activity_report", args=[self.target_user.pk])
        if self.request.user.pk == self.target_user.pk and not self.request.user.is_platform_admin:
            cancel_url = reverse("workspace_reports")

        context.update(
            title=f"Prepare Activity Report for {self.target_user}",
            eyebrow="Activity Reporting & Evaluation",
            description=f"Record deliverables, achievements, reflections, obstacles, and hours invested for {self.target_user.get_full_name() or self.target_user.email}.",
            submit_label="Save Activity Report",
            form_layout="grid",
            cancel_url=cancel_url,
        )
        return context


class UserActivityReportUpdateView(UpdateView):
    """Edit an existing user activity report."""

    model = UserActivityReport
    form_class = UserActivityReportForm
    pk_url_kwarg = "report_id"
    template_name = "core/admin/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(CustomUser, pk=kwargs["user_id"])
        self.report = get_object_or_404(UserActivityReport, pk=kwargs["report_id"], user=self.target_user)
        if not can_manage_user_activity_report(request.user, self.target_user, action="update", cohort=self.report.cohort):
            raise PermissionDenied("You do not have permission to edit this activity report.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return UserActivityReport.objects.filter(user=self.target_user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["target_user"] = self.target_user
        kwargs["is_reviewer"] = self.request.user.is_platform_admin or self.request.user.pk != self.target_user.pk
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.UPDATE,
            entity_type="Report",
            entity_name=self.object.title,
            entity_id=self.object.pk,
            cohort=self.object.cohort,
            description=f"Updated activity report '{self.object.title}' for {self.target_user}.",
        )
        messages.success(self.request, f"Activity report '{self.object.title}' updated successfully.")
        return response

    def get_success_url(self):
        if self.request.user.pk == self.target_user.pk and not self.request.user.is_platform_admin:
            return reverse("workspace_reports")
        return reverse("user_activity_report", args=[self.target_user.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cancel_url = reverse("user_activity_report", args=[self.target_user.pk])
        if self.request.user.pk == self.target_user.pk and not self.request.user.is_platform_admin:
            cancel_url = reverse("workspace_reports")

        context.update(
            title=f"Edit Activity Report: {self.object.title}",
            eyebrow=f"{self.target_user} · {self.object.cohort.name}",
            description="Update activity outcomes, reflections, challenges, or attached documentation.",
            submit_label="Update Report",
            form_layout="grid",
            cancel_url=cancel_url,
        )
        return context


class UserActivityReportDeleteView(DeleteView):
    """Delete an activity report."""

    model = UserActivityReport
    pk_url_kwarg = "report_id"
    http_method_names = ["post"]

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(CustomUser, pk=kwargs["user_id"])
        self.report = get_object_or_404(UserActivityReport, pk=kwargs["report_id"], user=self.target_user)
        if not can_manage_user_activity_report(request.user, self.target_user, action="delete", cohort=self.report.cohort):
            raise PermissionDenied("You do not have permission to delete this activity report.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return UserActivityReport.objects.filter(user=self.target_user)

    def form_valid(self, form):
        title = self.object.title
        cohort = self.object.cohort
        self.object.delete()
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.DELETE,
            entity_type="Report",
            entity_name=title,
            cohort=cohort,
            description=f"Deleted activity report '{title}' for {self.target_user}.",
        )
        messages.success(self.request, f"Activity report '{title}' deleted.")
        if self.request.user.pk == self.target_user.pk and not self.request.user.is_platform_admin:
            return redirect("workspace_reports")
        return redirect("user_activity_report", user_id=self.target_user.pk)


class UserActivityReportReviewView(UpdateView):
    """Leader or Admin evaluation and feedback on a submitted activity report."""

    model = UserActivityReport
    form_class = UserActivityReportReviewForm
    pk_url_kwarg = "report_id"
    template_name = "core/admin/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(CustomUser, pk=kwargs["user_id"])
        self.report = get_object_or_404(UserActivityReport, pk=kwargs["report_id"], user=self.target_user)
        if request.user.pk == self.target_user.pk and not request.user.is_platform_admin:
            raise PermissionDenied("You cannot review your own activity report.")
        if not can_manage_user_activity_report(request.user, self.target_user, action="update", cohort=self.report.cohort):
            raise PermissionDenied("You do not have permission to review activity reports for this user.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return UserActivityReport.objects.filter(user=self.target_user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["reviewer"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.UPDATE,
            entity_type="Report",
            entity_name=self.object.title,
            entity_id=self.object.pk,
            cohort=self.object.cohort,
            description=f"Reviewed activity report '{self.object.title}' for {self.target_user} (Status: {self.object.get_status_display()}).",
            details={"status": self.object.status, "feedback": self.object.feedback},
        )
        messages.success(self.request, f"Activity report reviewed as '{self.object.get_status_display()}'.")
        return response

    def get_success_url(self):
        return reverse("user_activity_report", args=[self.target_user.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=f"Review Report: {self.object.title}",
            eyebrow=f"Review & Evaluation · {self.target_user}",
            description=f"Provide evaluation feedback and approve or request revisions for {self.target_user}'s report on '{self.object.title}'.",
            submit_label="Save Evaluation & Feedback",
            form_layout="stack",
            cancel_url=reverse("user_activity_report", args=[self.target_user.pk]),
        )
        return context

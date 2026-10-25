from django import forms
from django.utils import timezone

from core.forms.base import StyledModelForm
from core.models import Cohort, CohortActivity, Term, UserActivityReport


class UserActivityReportForm(StyledModelForm):
    """Form for preparing and submitting an activity report for a participant."""

    field_wrapper_classes = {
        "summary": "form-field--full",
        "reflections": "form-field--full",
        "challenges": "form-field--full",
        "next_steps": "form-field--full",
        "attachment": "form-field--full",
    }

    class Meta:
        model = UserActivityReport
        fields = (
            "cohort",
            "term",
            "activity",
            "title",
            "report_date",
            "hours_spent",
            "progress_status",
            "status",
            "summary",
            "reflections",
            "challenges",
            "next_steps",
            "attachment",
        )
        widgets = {
            "report_date": forms.DateInput(attrs={"type": "date"}),
            "summary": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "What was achieved or worked on? List deliverables produced, tasks finished, and measurable outcomes.",
                }
            ),
            "reflections": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "What did you learn? Insights gained from mentors, peers, or personal reflections.",
                }
            ),
            "challenges": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "What obstacles or bottlenecks were faced and how were they addressed?",
                }
            ),
            "next_steps": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Upcoming commitments, action items, or goals for the next period.",
                }
            ),
        }

    def __init__(self, *args, target_user=None, fixed_cohort=None, is_reviewer=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_user = target_user

        if target_user:
            # Only cohorts the user actively belongs to
            user_cohorts = Cohort.objects.filter(
                memberships__user=target_user,
                memberships__is_active=True,
            ).distinct().select_related("chapter", "chapter__location", "chapter__location__program")
            self.fields["cohort"].queryset = user_cohorts
            if user_cohorts.count() == 1 and not self.initial.get("cohort"):
                self.initial["cohort"] = user_cohorts.first()

        selected_cohort = fixed_cohort or (
            self.data.get("cohort")
            or getattr(self.instance, "cohort", None)
            or self.initial.get("cohort")
        )
        if isinstance(selected_cohort, (int, str)) and str(selected_cohort).isdigit():
            selected_cohort = Cohort.objects.filter(pk=int(selected_cohort)).first()

        if selected_cohort:
            self.fields["term"].queryset = Term.objects.filter(
                cohort=selected_cohort, is_active=True
            ).order_by("sequence")
            self.fields["activity"].queryset = CohortActivity.objects.filter(
                cohort=selected_cohort
            ).order_by("term__sequence", "sequence", "title")
        elif target_user:
            self.fields["term"].queryset = Term.objects.filter(
                cohort__in=self.fields["cohort"].queryset, is_active=True
            ).order_by("cohort", "sequence")
            self.fields["activity"].queryset = CohortActivity.objects.filter(
                cohort__in=self.fields["cohort"].queryset
            ).order_by("cohort", "term__sequence", "sequence")
        else:
            self.fields["term"].queryset = Term.objects.filter(is_active=True).order_by("cohort", "sequence")
            self.fields["activity"].queryset = CohortActivity.objects.all().order_by("cohort", "sequence")

        # By default non-reviewers only see draft / submitted
        if not is_reviewer:
            self.fields["status"].choices = [
                (UserActivityReport.Status.SUBMITTED, "Submit Report for Review"),
                (UserActivityReport.Status.DRAFT, "Save as Draft"),
            ]

    def save(self, commit=True):
        if self.target_user and not self.instance.user_id:
            self.instance.user = self.target_user
        return super().save(commit=commit)


class UserActivityReportReviewForm(StyledModelForm):
    """Form for leaders/mentors/admins to evaluate, provide feedback, and approve activity reports."""

    field_wrapper_classes = {
        "feedback": "form-field--full",
    }

    class Meta:
        model = UserActivityReport
        fields = ("status", "feedback")
        widgets = {
            "feedback": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Provide qualitative feedback, evaluation notes, guidance, or commendations for this participant.",
                }
            ),
        }

    def __init__(self, *args, reviewer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.reviewer = reviewer
        self.fields["status"].choices = [
            (UserActivityReport.Status.APPROVED, "Approve Report"),
            (UserActivityReport.Status.REVIEWED, "Mark as Reviewed (Needs Revisions)"),
            (UserActivityReport.Status.DRAFT, "Return to Draft"),
        ]

    def save(self, commit=True):
        if self.reviewer:
            self.instance.reviewed_by = self.reviewer
        return super().save(commit=commit)

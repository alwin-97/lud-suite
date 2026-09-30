from django import forms
from django.db import transaction

from core.forms.base import StyledModelForm
from core.models import Cohort, CohortMembership, CustomUser


class PlatformUserForm(StyledModelForm):
    assignments = forms.MultipleChoiceField(
        label="Cohort roles",
        required=True,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select every role this user holds. A user may have multiple roles and cohorts.",
    )

    field_wrapper_classes = {"assignments": "form-field--full assignment-field"}

    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "is_active")
        help_texts = {
            "is_active": "Inactive users cannot sign in, even if they have cohort roles.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["assignments"].choices = self._assignment_choices()
        self.fields["assignments"].widget.attrs["class"] = "assignment-grid"

        if self.instance.pk:
            self.initial["assignments"] = [
                f"{cohort_id}:{role}"
                for cohort_id, role in self.instance.cohort_memberships.values_list(
                    "cohort_id", "role"
                )
            ]

    @staticmethod
    def _assignment_choices():
        choices = []
        cohorts = Cohort.objects.select_related("chapter", "chapter__location").order_by(
            "chapter__name", "-start_date", "name"
        )
        for cohort in cohorts:
            for role, role_label in CohortMembership.ROLE_CHOICES:
                label = (
                    f"{cohort.chapter.name} / {cohort.name} — {role_label}"
                    f" ({cohort.chapter.location.name})"
                )
                choices.append((f"{cohort.pk}:{role}", label))
        return choices

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        existing = CustomUser.objects.filter(email__iexact=email)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.role = ""
        if not user.pk:
            user.set_unusable_password()

        if not commit:
            return user

        user.save()
        selected_assignments = {
            (int(value.split(":", 1)[0]), value.split(":", 1)[1])
            for value in self.cleaned_data["assignments"]
        }
        user.cohort_memberships.exclude(
            cohort_id__in={cohort_id for cohort_id, _ in selected_assignments}
        ).delete()

        existing = {
            (membership.cohort_id, membership.role): membership
            for membership in user.cohort_memberships.all()
        }
        for key, membership in existing.items():
            if key not in selected_assignments:
                membership.delete()

        for cohort_id, role in selected_assignments:
            CohortMembership.objects.update_or_create(
                user=user,
                cohort_id=cohort_id,
                role=role,
                defaults={"is_active": True},
            )

        return user

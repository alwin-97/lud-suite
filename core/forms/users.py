from django import forms
from django.db import transaction
from django.db.models import Q

from core.forms.base import StyledModelForm
from core.models import ACTIVE_COHORT_CHAIN_FILTER, Cohort, CohortMembership, CustomUser


class AssignmentPicker(forms.CheckboxSelectMultiple):
    """Program -> location -> cohort role picker.

    ``locations`` is built by the form: a list of dicts with program, name and
    cohorts (each with its role options). Every checkbox stays in the page, so
    choices made under one location survive switching to another; the
    static/js/components/assignment-picker.js script only shows one location
    at a time. Without JavaScript every location is listed.
    """

    template_name = "components/forms/assignment_picker.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.locations = []

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        selected = {str(item) for item in (value or [])}
        locations = []
        for location in self.locations:
            cohorts = [
                {
                    **cohort,
                    "roles": [
                        {**role, "checked": role["value"] in selected}
                        for role in cohort["roles"]
                    ],
                }
                for cohort in location["cohorts"]
            ]
            locations.append({**location, "cohorts": cohorts})
        context["widget"]["locations"] = locations
        context["widget"]["programs"] = sorted({loc["program"] for loc in locations})
        context["widget"]["selected_count"] = len(selected)
        return context


class PlatformUserForm(StyledModelForm):
    assignments = forms.MultipleChoiceField(
        label="Cohort roles",
        required=True,
        widget=AssignmentPicker,
        help_text=(
            "Choose a program, then a location, then tick every role this person holds in "
            "that location's cohorts. Only active programs and locations are offered."
        ),
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
        current_cohort_ids = set()
        if self.instance.pk:
            self.initial["assignments"] = [
                f"{cohort_id}:{role}"
                for cohort_id, role in self.instance.cohort_memberships.values_list(
                    "cohort_id", "role"
                )
            ]
            current_cohort_ids = {
                int(value.split(":", 1)[0]) for value in self.initial["assignments"]
            }

        choices, locations = self._assignment_options(current_cohort_ids)
        self.fields["assignments"].choices = choices
        self.fields["assignments"].widget.locations = locations

    @staticmethod
    def _assignment_options(current_cohort_ids):
        """Cohorts a role can be given in: the whole chain (program, location,
        chapter, cohort) must be active. Cohorts the user already belongs to
        stay listed so saving never silently drops them."""
        cohorts = (
            Cohort.objects.filter(
                Q(**ACTIVE_COHORT_CHAIN_FILTER) | Q(pk__in=current_cohort_ids)
            )
            .select_related("chapter", "chapter__location", "chapter__location__program")
            .order_by(
                "chapter__location__program__name",
                "chapter__location__name",
                "chapter__name",
                "-start_date",
                "name",
            )
        )
        choices = []
        locations = {}
        for cohort in cohorts:
            location = cohort.chapter.location
            entry = locations.setdefault(
                location.pk,
                {
                    "key": location.pk,
                    "program": location.program.name,
                    "name": location.name,
                    "cohorts": [],
                },
            )
            roles = []
            for role, role_label in CohortMembership.ROLE_CHOICES:
                value = f"{cohort.pk}:{role}"
                choices.append((value, f"{cohort.name} — {role_label}"))
                roles.append({"value": value, "label": role_label})
            entry["cohorts"].append(
                {
                    "id": cohort.pk,
                    "name": cohort.name,
                    "chapter": cohort.chapter.name,
                    "dates": f"{cohort.start_date:%d %b %Y} – {cohort.end_date:%d %b %Y}",
                    "active": cohort.is_active and cohort.chapter.is_active,
                    "roles": roles,
                }
            )
        return choices, list(locations.values())

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if len(email) > 150:
            raise forms.ValidationError("Email address cannot exceed 150 characters.")
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

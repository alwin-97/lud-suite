from django import forms
from django.db.models import Exists, OuterRef, Prefetch

from core.forms.base import StyledModelForm
from core.models import Chapter, Cohort, CohortMembership, CustomUser, Location, Program


class ProgramForm(StyledModelForm):
    class Meta:
        model = Program
        fields = ("name", "description", "duration_months", "is_active")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class LocationForm(StyledModelForm):
    class Meta:
        model = Location
        fields = ("program", "name", "is_active")


class ChapterForm(StyledModelForm):
    class Meta:
        model = Chapter
        fields = ("name", "location", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = Location.objects.select_related("program")


class CohortForm(StyledModelForm):
    class Meta:
        model = Cohort
        fields = ("name", "chapter", "start_date", "end_date", "is_active")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "end_date": "Leave blank to use the program's cohort length from the start date.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chapter"].queryset = Chapter.objects.select_related(
            "location", "location__program"
        )

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end <= start:
            self.add_error("end_date", "The end date must be after the start date.")
        return cleaned


class MemberSelect(forms.Select):
    """User select that tags each option with a group (linked to this location
    or not) and a one-line summary of the person's existing affiliations, which
    static/js/components/searchable-select.js renders."""

    def __init__(self, *args, cohort=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cohort = cohort

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        user = getattr(value, "instance", None)
        if user is not None and self.cohort is not None:
            location = self.cohort.chapter.location
            option["attrs"]["data-group"] = (
                f"Linked to {location.name}" if user.linked else "Other users"
            )
            option["attrs"]["data-meta"] = self.summary(user)
        return option

    def summary(self, user):
        in_cohort = []
        elsewhere = {}
        for membership in user.cohort_memberships.all():
            if not membership.is_active:
                continue
            role = membership.get_role_display()
            if membership.cohort_id == self.cohort.pk:
                in_cohort.append(role)
                continue
            location = membership.cohort.chapter.location
            key = f"{location.program.name} · {location.name}"
            elsewhere.setdefault(key, [])
            if role not in elsewhere[key]:
                elsewhere[key].append(role)
        parts = []
        if in_cohort:
            parts.append("Already in this cohort: " + ", ".join(in_cohort))
        parts.extend(f"{key} — {', '.join(roles)}" for key, roles in elsewhere.items())
        return " | ".join(parts)


class CohortMemberForm(StyledModelForm):
    """Adds one role for one user to a cohort (the cohort comes from the page)."""

    class Meta:
        model = CohortMembership
        fields = ("user", "role")

    def __init__(self, *args, cohort, **kwargs):
        super().__init__(*args, **kwargs)
        self.cohort = cohort
        linked = CohortMembership.objects.filter(
            user=OuterRef("pk"), cohort__chapter__location=cohort.chapter.location
        )
        self.fields["user"].queryset = (
            CustomUser.objects.filter(is_active=True, is_superuser=False)
            .exclude(role=CustomUser.ADMIN)
            .annotate(linked=Exists(linked))
            .prefetch_related(
                Prefetch(
                    "cohort_memberships",
                    queryset=CohortMembership.objects.select_related(
                        "cohort__chapter__location__program"
                    ),
                )
            )
            .order_by("-linked", "first_name", "last_name", "email")
        )
        widget = MemberSelect(
            cohort=cohort, attrs={"class": "form-control", "data-searchable": ""}
        )
        widget.choices = self.fields["user"].choices
        self.fields["user"].widget = widget
        self.fields["user"].label_from_instance = lambda user: (
            f"{user.get_full_name()} ({user.email})" if user.get_full_name() else user.email
        )

    def clean(self):
        cleaned = super().clean()
        user, role = cleaned.get("user"), cleaned.get("role")
        if user and role:
            existing = CohortMembership.objects.filter(
                user=user, cohort=self.cohort, role=role
            ).first()
            if existing and existing.is_active:
                raise forms.ValidationError(
                    f"{user} is already a {existing.get_role_display()} in this cohort."
                )
            self.existing = existing
        return cleaned

    def save(self, commit=True):
        existing = getattr(self, "existing", None)
        if existing:
            existing.is_active = True
            existing.save(update_fields=["is_active"])
            return existing
        self.instance.cohort = self.cohort
        return super().save(commit)

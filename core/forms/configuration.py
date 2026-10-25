from django import forms
from django.db.models import Exists, OuterRef, Prefetch

from core.forms.base import StyledModelForm
from core.models import (
    Chapter,
    Cohort,
    CohortActivity,
    CohortMembership,
    CustomUser,
    Location,
    MentorAssignment,
    Program,
    Term,
    TermResource,
)


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


class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class TermForm(StyledModelForm):
    upload_files = MultipleFileField(
        required=False,
        label="Attach files (documents & images)",
        help_text="Select one or more documents or image files to attach.",
    )
    links = forms.CharField(
        required=False,
        label="Attach links / URLs",
        help_text="Add external links (one per line, e.g. 'Syllabus | https://example.com' or just 'https://example.com').",
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Title | https://example.com"}),
    )

    field_wrapper_classes = {
        "description": "form-field--full",
        "upload_files": "form-field--full",
        "links": "form-field--full",
    }

    class Meta:
        model = Term
        fields = ("name", "sequence", "start_date", "end_date", "description", "is_active")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, cohort=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cohort = cohort
        if not self.instance.pk and cohort:
            next_seq = (
                cohort.terms.order_by("-sequence").values_list("sequence", flat=True).first()
                or 0
            ) + 1
            self.initial.setdefault("sequence", next_seq)
            self.initial.setdefault("name", f"Term {next_seq}")

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end <= start:
            self.add_error("end_date", "The end date must be after the start date.")
        return cleaned

    def save(self, commit=True):
        if self.cohort and not self.instance.cohort_id:
            self.instance.cohort = self.cohort
        term = super().save(commit=commit)
        if commit:
            self._save_attachments(term)
        return term

    def _save_attachments(self, term):
        files = self.files.getlist("upload_files")
        for uploaded_file in files:
            ext = ""
            if "." in uploaded_file.name:
                ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
            is_img = ext in TermResource.IMAGE_EXTENSIONS
            resource_type = TermResource.IMAGE if is_img else TermResource.DOCUMENT
            base_name = uploaded_file.name.rsplit(".", 1)[0]
            clean_title = base_name.replace("_", " ").replace("-", " ").capitalize()
            TermResource.objects.create(
                term=term,
                title=clean_title or uploaded_file.name,
                resource_type=resource_type,
                file=uploaded_file,
            )

        links_text = self.cleaned_data.get("links", "")
        for line in links_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                parts = line.split("|", 1)
                title, url = parts[0].strip(), parts[1].strip()
            else:
                title, url = line, line
            if url:
                if not (url.startswith("http://") or url.startswith("https://")):
                    url = "https://" + url
                TermResource.objects.create(
                    term=term,
                    title=title,
                    resource_type=TermResource.LINK,
                    url=url,
                )


class TermResourceForm(StyledModelForm):
    class Meta:
        model = TermResource
        fields = ("title", "resource_type", "file", "url", "description")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, term=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.term = term
        self.fields["title"].required = True

    def clean(self):
        cleaned = super().clean()
        resource_type = cleaned.get("resource_type")
        file = cleaned.get("file")
        url = cleaned.get("url")

        if resource_type in (TermResource.DOCUMENT, TermResource.IMAGE) and not file:
            self.add_error("file", f"Please upload a file for {resource_type}.")
        elif resource_type == TermResource.LINK and not url:
            self.add_error("url", "Please provide a valid URL for this link.")

        return cleaned

    def save(self, commit=True):
        if self.term and not self.instance.term_id:
            self.instance.term = self.term
        return super().save(commit=commit)


class CohortMemberReallocateForm(StyledModelForm):
    """Reallocate member role or transfer to another cohort."""

    target_cohort = forms.ModelChoiceField(
        queryset=Cohort.objects.filter(is_active=True).select_related(
            "chapter", "chapter__location", "chapter__location__program"
        ),
        required=False,
        label="Reallocate to another cohort (optional)",
        help_text="Select a target cohort to transfer this member, or leave blank to keep in current cohort.",
    )

    class Meta:
        model = CohortMembership
        fields = ("role",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["target_cohort"] = self.instance.cohort


class CohortActivityForm(StyledModelForm):
    """Plan an activity / milestone on the cohort timeline for a specific term."""

    field_wrapper_classes = {
        "description": "form-field--full",
    }

    class Meta:
        model = CohortActivity
        fields = (
            "term",
            "title",
            "target_audience",
            "status",
            "start_date",
            "end_date",
            "sequence",
            "description",
        )
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, cohort=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cohort = cohort
        if cohort:
            self.fields["term"].queryset = cohort.terms.filter(is_active=True).order_by("sequence")
            if not self.instance.pk:
                first_term = cohort.terms.filter(is_active=True).order_by("sequence").first()
                if first_term:
                    self.initial.setdefault("term", first_term.pk)

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "Activity end date cannot be earlier than start date.")
        return cleaned

    def save(self, commit=True):
        if self.cohort and not self.instance.cohort_id:
            self.instance.cohort = self.cohort
        return super().save(commit=commit)


class MentorAssignmentForm(StyledModelForm):
    mentor = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        label="Select Mentor",
        help_text="Choose an active mentor from this cohort.",
    )
    mentee = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        label="Select Mentee",
        help_text="Choose an active mentee from this cohort.",
    )

    class Meta:
        model = MentorAssignment
        fields = ("mentor", "mentee", "notes")
        widgets = {
            "notes": forms.TextInput(attrs={"placeholder": "Mentorship goals or focus area (optional)..."}),
        }

    def __init__(self, *args, cohort=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cohort = cohort
        if cohort:
            self.fields["mentor"].queryset = cohort.get_mentors()
            self.fields["mentee"].queryset = cohort.get_mentees()

    def clean(self):
        cleaned = super().clean()
        mentor = cleaned.get("mentor")
        mentee = cleaned.get("mentee")
        if mentor and mentee and mentor.pk == mentee.pk:
            self.add_error("mentee", "A user cannot be assigned as their own mentor.")
        return cleaned

    def save(self, commit=True):
        if self.cohort and not self.instance.cohort_id:
            self.instance.cohort = self.cohort
        return super().save(commit=commit)




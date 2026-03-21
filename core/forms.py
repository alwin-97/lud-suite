from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import (
    CustomUser,
    Activity,
    Notification,
    WorkSchedule,
    WorkScheduleAssignment,
    ObjectiveItem,
    YearPlanItem,
    StatusConfig,
    MenteeAssessment,
    MentorMenteeAssignment,
    SessionType,
    RatingDomain,
    DomainIndicator,
    RatingScaleDefinition,
    MoodCategory,
    ReferenceContent,
    TemplateConfig,
    School,
    Location,
    Chapter,
    AcademicCycle,
    Programme,
    ReflectiveReport,
    DiaryEntry,
    VolunteerTranscript,
    ProfileArtifact,
    RepositoryAsset,
    VolunteerReportingAssignment,
)
from decimal import Decimal
User = get_user_model()


# -------------------- Activity Form --------------------
class ActivityForm(forms.ModelForm):
    
    class Meta:
        model = Activity
        fields = ["date", "duration", "activity", "other_activity", "learnings", "photo", "feedback"]
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "duration": forms.Select(
                attrs={"class": "form-control"},
                choices=[(Decimal(x)/Decimal(4), f"{Decimal(x)/Decimal(4)}") for x in range(1, 33)]
            ),
            "activity": forms.Select(attrs={"class": "form-control"}, choices=[
                ("YCLP-Class", "YCLP-Class"),
                ("DREAMS Summer Camp", "DREAMS Summer Camp"),
                ("DREAMS Follow-Up", "DREAMS Follow-Up"),
                ("Others", "Others"),
            ]),
            "other_activity": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "learnings": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "feedback": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


# -------------------- Admin Add User Form --------------------
class AdminAddUserForm(UserCreationForm):
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role', 'password1', 'password2']


# -------------------- Profile Form --------------------
class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            "first_name", "last_name", "email", "phone", "role",
            "gender", "date_of_birth", "religion",
            "institution", "designation", "permanent_address", "profile_pic"
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "gender": forms.Select(
                choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
                attrs={"class": "form-select"}
            ),
            "religion": forms.TextInput(attrs={"class": "form-control"}),
            "institution": forms.TextInput(attrs={"class": "form-control"}),
            "designation": forms.TextInput(attrs={"class": "form-control"}),
            "permanent_address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Disable fields that should not be edited
        for field in ["first_name", "last_name", "email", "phone", "role"]:
            self.fields[field].disabled = True


# -------------------- Work Schedule Form --------------------
class WorkScheduleForm(forms.ModelForm):
    assignees = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True
    )

    class Meta:
        model = WorkSchedule
        fields = ['role', 'due_date', 'description']
        widgets = {
            'role': forms.TextInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}  # calendar picker
            ),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        creator = kwargs.pop("creator", None)
        if creator is None:
            creator = kwargs.pop("endorser", None)
        super().__init__(*args, **kwargs)
        if creator:
            if creator.role == "admin":
                assignee_queryset = User.objects.exclude(role="admin")
            else:
                assignee_queryset = User.objects.filter(
                    Q(role="mentor") | Q(role="volunteer", reporting_assignment__endorser=creator)
                )
            self.fields["assignees"].queryset = assignee_queryset.distinct().order_by("first_name", "username")
        if self.instance.pk:
            self.fields["assignees"].initial = self.instance.mentors.all()
        self.fields['assignees'].label_from_instance = (
            lambda obj: f"{obj.get_full_name() or obj.username} ({obj.get_role_display()})"
        )


class WorkScheduleAssignmentUpdateForm(forms.ModelForm):
    class Meta:
        model = WorkScheduleAssignment
        fields = ["status", "progress_note"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "progress_note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


# -------------------- DIP Objective / Year Plan Forms --------------------
class ObjectiveItemForm(forms.ModelForm):
    class Meta:
        model = ObjectiveItem
        fields = [
            "objective_title",
            "objective_text",
            "action_items",
            "start_date",
            "end_date",
            "expected_outcome",
            "status",
            "progress_percent",
            "evidence",
            "mentee_remarks",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "progress_percent": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
            "objective_title": forms.TextInput(attrs={"class": "form-control"}),
            "objective_text": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "action_items": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "expected_outcome": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "mentee_remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "evidence": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "status" in self.fields:
            self.fields["status"].queryset = StatusConfig.objects.filter(is_active=True)


class ObjectiveItemMentorForm(forms.ModelForm):
    class Meta:
        model = ObjectiveItem
        fields = ["status", "mentor_comments", "mentor_approved"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "mentor_comments": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "status" in self.fields:
            self.fields["status"].queryset = StatusConfig.objects.filter(is_active=True)


class YearPlanItemForm(forms.ModelForm):
    class Meta:
        model = YearPlanItem
        fields = [
            "year",
            "milestone",
            "deliverable",
            "target_date",
            "target_period",
            "status",
            "remarks",
        ]
        widgets = {
            "year": forms.Select(attrs={"class": "form-select"}),
            "milestone": forms.TextInput(attrs={"class": "form-control"}),
            "deliverable": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "target_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "target_period": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "status" in self.fields:
            self.fields["status"].queryset = StatusConfig.objects.filter(is_active=True)


class YearPlanItemMentorForm(forms.ModelForm):
    class Meta:
        model = YearPlanItem
        fields = ["status", "mentor_comments", "review_date"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "mentor_comments": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "review_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "status" in self.fields:
            self.fields["status"].queryset = StatusConfig.objects.filter(is_active=True)


class MenteeAssessmentForm(forms.ModelForm):
    class Meta:
        model = MenteeAssessment
        fields = [
            "year",
            "session_type",
            "date",
            "theme_topic",
            "beginning_mood",
            "end_mood",
            "mentor_remarks",
            "action_plan",
        ]
        widgets = {
            "year": forms.Select(attrs={"class": "form-select"}),
            "session_type": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "theme_topic": forms.TextInput(attrs={"class": "form-control"}),
            "beginning_mood": forms.TextInput(attrs={"class": "form-control"}),
            "end_mood": forms.TextInput(attrs={"class": "form-control"}),
            "mentor_remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "action_plan": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mood_choices = [
            (category.name, category.name)
            for category in MoodCategory.objects.order_by("sort_order", "name")
        ]
        if mood_choices:
            select_widget = forms.Select(attrs={"class": "form-select"})
            self.fields["beginning_mood"] = forms.ChoiceField(
                choices=[("", "Select")] + mood_choices,
                required=False,
                widget=select_widget,
            )
            self.fields["end_mood"] = forms.ChoiceField(
                choices=[("", "Select")] + mood_choices,
                required=False,
                widget=forms.Select(attrs={"class": "form-select"}),
            )
            self.initial.setdefault("beginning_mood", self.instance.beginning_mood if self.instance.pk else "")
            self.initial.setdefault("end_mood", self.instance.end_mood if self.instance.pk else "")


# -------------------- Admin Config Forms --------------------
class MentorMenteeAssignmentForm(forms.ModelForm):
    class Meta:
        model = MentorMenteeAssignment
        fields = ["mentor", "mentee", "start_date", "end_date", "is_active"]
        widgets = {
            "mentor": forms.Select(attrs={"class": "form-select"}),
            "mentee": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class VolunteerReportingAssignmentForm(forms.ModelForm):
    class Meta:
        model = VolunteerReportingAssignment
        fields = ["volunteer", "programme", "location", "endorser"]
        widgets = {
            "volunteer": forms.Select(attrs={"class": "form-select"}),
            "programme": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "endorser": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["volunteer"].queryset = User.objects.filter(role="volunteer").order_by("first_name", "username")
        self.fields["programme"].queryset = Programme.objects.filter(is_active=True).order_by("name")
        self.fields["location"].queryset = Location.objects.filter(is_active=True).order_by("name")
        self.fields["endorser"].queryset = User.objects.filter(role="endorser").order_by("first_name", "username")


class StatusConfigForm(forms.ModelForm):
    class Meta:
        model = StatusConfig
        fields = ["name", "color", "ordering", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "color": forms.TextInput(attrs={"class": "form-control"}),
            "ordering": forms.NumberInput(attrs={"class": "form-control"}),
        }


class SessionTypeForm(forms.ModelForm):
    class Meta:
        model = SessionType
        fields = ["name", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }


class RatingDomainForm(forms.ModelForm):
    class Meta:
        model = RatingDomain
        fields = ["year", "name", "source", "sort_order", "is_active"]
        widgets = {
            "year": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "source": forms.Select(attrs={"class": "form-select"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class DomainIndicatorForm(forms.ModelForm):
    class Meta:
        model = DomainIndicator
        fields = ["domain", "description", "sort_order"]
        widgets = {
            "domain": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class RatingScaleDefinitionForm(forms.ModelForm):
    class Meta:
        model = RatingScaleDefinition
        fields = ["domain", "score", "description"]
        widgets = {
            "domain": forms.Select(attrs={"class": "form-select"}),
            "score": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class MoodCategoryForm(forms.ModelForm):
    class Meta:
        model = MoodCategory
        fields = ["name", "description", "mood_types", "sort_order"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "mood_types": forms.TextInput(attrs={"class": "form-control"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class ReferenceContentForm(forms.ModelForm):
    class Meta:
        model = ReferenceContent
        fields = ["section", "title", "content", "sort_order"]
        widgets = {
            "section": forms.TextInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class TemplateConfigForm(forms.ModelForm):
    class Meta:
        model = TemplateConfig
        fields = ["name", "scope", "year", "fields_config", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "scope": forms.Select(attrs={"class": "form-select"}),
            "year": forms.Select(attrs={"class": "form-select"}),
            "fields_config": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


# -------------------- New Config Forms (SRS FR-03) --------------------
class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
        }


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["name", "code", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
        }


class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapter
        fields = ["name", "code", "school", "location", "leader", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "school": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "leader": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["leader"].queryset = User.objects.filter(
            role__in=["mentor", "endorser"]
        )
        self.fields["leader"].required = False


class AcademicCycleForm(forms.ModelForm):
    class Meta:
        model = AcademicCycle
        fields = ["year_label", "start_date", "end_date", "is_active"]
        widgets = {
            "year_label": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class ProgrammeForm(forms.ModelForm):
    class Meta:
        model = Programme
        fields = ["name", "code", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ["subject", "message", "target_group"]
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control", "placeholder": "Notification subject"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Enter message..."}),
            "target_group": forms.Select(attrs={"class": "form-select"}),
        }


# -------------------- Reflective Report Form --------------------
class ReflectiveReportForm(forms.ModelForm):
    class Meta:
        model = ReflectiveReport
        fields = [
            "activity_name",
            "duration",
            "date",
            "learnings",
            "feedback",
            "suggestions",
            "photo",
        ]
        widgets = {
            "activity_name": forms.TextInput(attrs={"class": "form-control"}),
            "duration": forms.NumberInput(attrs={"class": "form-control", "step": "0.25"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "learnings": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "feedback": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "suggestions": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop("user", None)
        super().__init__(*args, **kwargs)


# -------------------- Work Diary Form --------------------
class DiaryEntryForm(forms.ModelForm):
    class Meta:
        model = DiaryEntry
        fields = ["date", "duration", "linked_activity", "narrative_entry", "evidence"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "duration": forms.NumberInput(attrs={"class": "form-control", "step": "0.25"}),
            "linked_activity": forms.TextInput(attrs={"class": "form-control"}),
            "narrative_entry": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "evidence": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop("user", None)
        super().__init__(*args, **kwargs)


# -------------------- Volunteer Transcript Form --------------------
class VolunteerTranscriptForm(forms.ModelForm):
    class Meta:
        model = VolunteerTranscript
        fields = ["template_choice", "generated_summary", "reviewer_notes", "approval_status", "export_file"]
        widgets = {
            "template_choice": forms.TextInput(attrs={"class": "form-control"}),
            "generated_summary": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "reviewer_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "approval_status": forms.Select(attrs={"class": "form-select"}),
            "export_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


# -------------------- Profile Artifact Form --------------------
class ProfileArtifactForm(forms.ModelForm):
    class Meta:
        model = ProfileArtifact
        fields = ["title", "document", "is_public"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "document": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


# -------------------- Repository Form --------------------
class RepositoryAssetForm(forms.ModelForm):
    class Meta:
        model = RepositoryAsset
        fields = ["title", "category", "file_upload", "tags", "role_visibility"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "file_upload": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "tags": forms.TextInput(attrs={"class": "form-control", "placeholder": "comma separated tags"}),
            "role_visibility": forms.Select(attrs={"class": "form-select"}),
        }

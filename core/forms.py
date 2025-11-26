from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import (
    CustomUser, Activity, Notification, WorkSchedule
)
from decimal import Decimal
User = get_user_model()


# -------------------- Notification Form --------------------
class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ["message", "target_group"]
        widgets = {
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Enter instructions..."}),
            "target_group": forms.Select(attrs={"class": "form-select"}),
        }


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
    mentors = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True
    )

    class Meta:
        model = WorkSchedule
        fields = ['mentors', 'role', 'due_date', 'description']
        widgets = {
            'role': forms.TextInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}  # 👈 calendar picker
            ),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        endorser = kwargs.pop('endorser', None)
        super().__init__(*args, **kwargs)
        if endorser:
            # ✅ Show only mentors assigned to this endorser (using your CustomUser.mentors M2M field)
            self.fields['mentors'].queryset = endorser.mentors.filter(role='mentor')
        self.fields['mentors'].label_from_instance = lambda obj: obj.email

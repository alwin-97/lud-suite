from django import forms
from .models import Activity
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
# core/forms.py
from django import forms
from .models import Notification
from django.contrib.auth import get_user_model

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ["message", "target_group"]
        widgets = {
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Enter instructions..."}),
            "target_group": forms.Select(attrs={"class": "form-select"}),
        }


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["date", "duration", "activity", "other_activity", "learnings", "photo", "feedback"]
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "duration": forms.Select(attrs={"class": "form-control"}, choices=[(x/4, x/4) for x in range(1, 33)]),
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
class AdminAddUserForm(UserCreationForm):
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role', 'password1', 'password2']

User = get_user_model()

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
        self.fields["first_name"].disabled = True
        self.fields["last_name"].disabled = True
        self.fields["email"].disabled = True
        self.fields["phone"].disabled = True
        self.fields["role"].disabled = True
class WorkScheduleForm(forms.Form):
    mentors = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role='mentor'),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )
    role = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    due_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
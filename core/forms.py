from django import forms
from .models import Activity

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

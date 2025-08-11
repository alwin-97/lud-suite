from django import forms
from .models import Activity

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['date', 'duration', 'activity', 'other_activity', 'learnings', 'photo', 'feedback']

    def clean(self):
        cleaned_data = super().clean()
        activity = cleaned_data.get("activity")
        other_activity = cleaned_data.get("other_activity")

        if activity == "Others" and not other_activity:
            self.add_error('other_activity', "Please specify the activity if 'Others' is selected.")

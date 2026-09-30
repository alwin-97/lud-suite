from django import forms

from core.forms.base import StyledModelForm
from core.models import Chapter, Cohort, Location


class LocationForm(StyledModelForm):
    class Meta:
        model = Location
        fields = ("name", "is_active")


class ChapterForm(StyledModelForm):
    class Meta:
        model = Chapter
        fields = ("name", "location", "is_active")


class CohortForm(StyledModelForm):
    class Meta:
        model = Cohort
        fields = ("name", "chapter", "start_date", "is_active")
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"})}
        help_texts = {
            "start_date": "The end date is calculated automatically, three years later.",
        }

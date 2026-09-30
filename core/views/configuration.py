from django.db.models import Count, Q
from django.views.generic import ListView, TemplateView

from core.forms import ChapterForm, CohortForm, LocationForm
from core.models import Chapter, Cohort, Location
from core.permissions import AdminRequiredMixin
from core.views.mixins import AdminCreateView, AdminDeleteView, AdminUpdateView


class ConfigurationHomeView(AdminRequiredMixin, TemplateView):
    template_name = "core/admin/configuration/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            location_count=Location.objects.count(),
            chapter_count=Chapter.objects.count(),
            cohort_count=Cohort.objects.count(),
        )
        return context


# Locations -----------------------------------------------------------------

class LocationListView(AdminRequiredMixin, ListView):
    queryset = Location.objects.annotate(chapter_count=Count("chapters"))
    template_name = "core/admin/configuration/location_list.html"
    context_object_name = "locations"


class LocationCreateView(AdminCreateView):
    model = Location
    form_class = LocationForm
    list_url_name = "location_list"


class LocationUpdateView(AdminUpdateView):
    model = Location
    form_class = LocationForm
    list_url_name = "location_list"


class LocationDeleteView(AdminDeleteView):
    model = Location
    list_url_name = "location_list"
    protected_message = "This location is in use by a chapter. Deactivate it instead."


# Chapters ------------------------------------------------------------------

class ChapterListView(AdminRequiredMixin, ListView):
    queryset = Chapter.objects.select_related("location").annotate(
        cohort_count=Count("cohorts")
    )
    template_name = "core/admin/configuration/chapter_list.html"
    context_object_name = "chapters"


class ChapterCreateView(AdminCreateView):
    model = Chapter
    form_class = ChapterForm
    list_url_name = "chapter_list"


class ChapterUpdateView(AdminUpdateView):
    model = Chapter
    form_class = ChapterForm
    list_url_name = "chapter_list"


class ChapterDeleteView(AdminDeleteView):
    model = Chapter
    list_url_name = "chapter_list"
    protected_message = "This chapter has cohorts. Deactivate it instead."


# Cohorts -------------------------------------------------------------------

class CohortListView(AdminRequiredMixin, ListView):
    queryset = Cohort.objects.select_related("chapter", "chapter__location").annotate(
        user_count=Count(
            "memberships__user",
            filter=Q(memberships__is_active=True),
            distinct=True,
        )
    )
    template_name = "core/admin/configuration/cohort_list.html"
    context_object_name = "cohorts"


class CohortCreateView(AdminCreateView):
    model = Cohort
    form_class = CohortForm
    list_url_name = "cohort_list"


class CohortUpdateView(AdminUpdateView):
    model = Cohort
    form_class = CohortForm
    list_url_name = "cohort_list"


class CohortDeleteView(AdminDeleteView):
    model = Cohort
    list_url_name = "cohort_list"

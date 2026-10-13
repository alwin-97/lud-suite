from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from core.forms import ChapterForm, CohortForm, CohortMemberForm, LocationForm, ProgramForm
from core.models import Chapter, Cohort, CohortMembership, Location, Program
from core.permissions import AdminRequiredMixin
from core.views.mixins import AdminCreateView, AdminDeleteView, AdminUpdateView


class ConfigurationHomeView(AdminRequiredMixin, TemplateView):
    template_name = "core/admin/configuration/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            program_count=Program.objects.count(),
            location_count=Location.objects.count(),
            chapter_count=Chapter.objects.count(),
            cohort_count=Cohort.objects.count(),
        )
        return context


# Programs ------------------------------------------------------------------

class ProgramListView(AdminRequiredMixin, ListView):
    queryset = Program.objects.annotate(
        location_count=Count("locations", distinct=True),
        cohort_count=Count("locations__chapters__cohorts", distinct=True),
    )
    template_name = "core/admin/configuration/program_list.html"
    context_object_name = "programs"


class ProgramCreateView(AdminCreateView):
    model = Program
    form_class = ProgramForm
    list_url_name = "program_list"


class ProgramUpdateView(AdminUpdateView):
    model = Program
    form_class = ProgramForm
    list_url_name = "program_list"


class ProgramDeleteView(AdminDeleteView):
    model = Program
    list_url_name = "program_list"
    protected_message = "This program has locations. Deactivate it instead."


# Locations -----------------------------------------------------------------

class LocationListView(AdminRequiredMixin, ListView):
    queryset = Location.objects.select_related("program").annotate(
        chapter_count=Count("chapters")
    )
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
    queryset = Chapter.objects.select_related("location", "location__program").annotate(
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
    queryset = Cohort.objects.select_related(
        "chapter", "chapter__location", "chapter__location__program"
    ).annotate(
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


class CohortManageView(AdminRequiredMixin, DetailView):
    """One cohort and its members: add a role, switch it on/off, or remove it."""

    queryset = Cohort.objects.select_related(
        "chapter", "chapter__location", "chapter__location__program"
    )
    pk_url_kwarg = "cohort_id"
    template_name = "core/admin/configuration/cohort_manage.html"
    context_object_name = "cohort"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CohortMemberForm(request.POST, cohort=self.object)
        if form.is_valid():
            membership = form.save()
            messages.success(
                request,
                f"{membership.user} added as {membership.get_role_display()}.",
            )
            return redirect("cohort_manage", cohort_id=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or CohortMemberForm(cohort=self.object)
        memberships = list(
            self.object.memberships.select_related("user").order_by(
                "user__first_name", "user__last_name", "user__email", "role"
            )
        )
        context["memberships"] = memberships
        context["active_member_count"] = sum(m.is_active for m in memberships)
        context["role_counts"] = [
            (label, sum(m.is_active and m.role == code for m in memberships))
            for code, label in CohortMembership.ROLE_CHOICES
        ]
        return context


class CohortMemberActionView(AdminRequiredMixin, View):
    """POST-only: action is "toggle" (activate/deactivate) or "remove"."""

    http_method_names = ["post"]
    action = ""

    def post(self, request, cohort_id, membership_id):
        membership = get_object_or_404(
            CohortMembership.objects.select_related("user"),
            pk=membership_id,
            cohort_id=cohort_id,
        )
        if self.action == "remove":
            membership.delete()
            messages.success(request, f"{membership.user}'s {membership.get_role_display()} role removed.")
        else:
            membership.is_active = not membership.is_active
            membership.save(update_fields=["is_active"])
            state = "activated" if membership.is_active else "deactivated"
            messages.success(request, f"{membership.user}'s {membership.get_role_display()} role {state}.")
        return redirect(reverse("cohort_manage", args=[cohort_id]))

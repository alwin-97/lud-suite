from django.views.generic import TemplateView

from core.models import Chapter, Cohort, CustomUser, Location, Program
from core.permissions import AdminRequiredMixin


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = "core/admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        first_name = self.request.user.first_name
        context.update(
            title=f"Welcome, {first_name}." if first_name else "Welcome.",
            program_count=Program.objects.filter(is_active=True).count(),
            location_count=Location.objects.filter(is_active=True).count(),
            chapter_count=Chapter.objects.filter(is_active=True).count(),
            cohort_count=Cohort.objects.filter(is_active=True).count(),
            user_count=CustomUser.objects.filter(
                is_active=True,
                cohort_memberships__is_active=True,
            ).distinct().count(),
        )
        return context

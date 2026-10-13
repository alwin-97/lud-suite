from django.db.models import Prefetch
from django.views.generic import ListView

from core.forms import PlatformUserForm
from core.models import CohortMembership, CustomUser
from core.permissions import AdminRequiredMixin
from core.views.mixins import AdminCreateView, AdminUpdateView


def platform_users():
    """Users managed on these pages: never platform admins or superusers."""
    return CustomUser.objects.exclude(role=CustomUser.ADMIN).filter(is_superuser=False)


class PlatformUserListView(AdminRequiredMixin, ListView):
    template_name = "core/admin/users/list.html"
    context_object_name = "platform_users"

    def get_queryset(self):
        return platform_users().prefetch_related(
            Prefetch(
                "cohort_memberships",
                queryset=CohortMembership.objects.filter(is_active=True).select_related(
                    "cohort",
                    "cohort__chapter",
                    "cohort__chapter__location",
                    "cohort__chapter__location__program",
                ),
            )
        ).order_by("first_name", "last_name", "email")


class PlatformUserFormMixin:
    model = CustomUser
    form_class = PlatformUserForm
    list_url_name = "platform_user_list"
    eyebrow = "Access management"
    description = "The email must match the Google account this person will use."
    submit_label = "Save user"
    form_layout = "grid"


class PlatformUserCreateView(PlatformUserFormMixin, AdminCreateView):
    success_message = "User provisioned successfully. They can now sign in with Google."


class PlatformUserUpdateView(PlatformUserFormMixin, AdminUpdateView):
    success_message = "User access updated successfully."

    def get_queryset(self):
        return platform_users()

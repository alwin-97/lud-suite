from django.db.models import Prefetch
from django.db import transaction
from django.views.generic import ListView

from core.forms import PlatformUserForm
from core.models import ChangeHistory, CohortMembership, CustomUser, ScopeMembership, log_change
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
            ),
            Prefetch("scope_memberships", queryset=ScopeMembership.objects.filter(is_active=True).select_related("program", "location__program", "chapter__location__program")),
        ).order_by("first_name", "last_name", "email")


class PlatformUserFormMixin:
    model = CustomUser
    form_class = PlatformUserForm
    list_url_name = "platform_user_list"
    eyebrow = "Access management"
    description = "The email must match the Google account this person will use."
    submit_label = "Save user"
    form_layout = "grid"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["actor"] = self.request.user
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        previous = CustomUser.objects.filter(pk=form.instance.pk).values("is_active", "email", "first_name", "last_name").first()
        response = super().form_valid(form)
        if previous:
            changes = {name: {"before": before, "after": getattr(self.object, name)}
                       for name, before in previous.items() if before != getattr(self.object, name)}
            if changes:
                action = ChangeHistory.Action.UPDATE
                if "is_active" in changes:
                    action = ChangeHistory.Action.ACTIVATE if self.object.is_active else ChangeHistory.Action.DEACTIVATE
                log_change(self.request.user, action, "User", str(self.object),
                           f"Changed account details for {self.object.email}.", entity_id=self.object.pk,
                           details={"user_id": self.object.pk, "changes": changes})
        return response


class PlatformUserCreateView(PlatformUserFormMixin, AdminCreateView):
    success_message = "User provisioned successfully. They can now sign in with Google."


class PlatformUserUpdateView(PlatformUserFormMixin, AdminUpdateView):
    success_message = "User access updated successfully."

    def get_queryset(self):
        return platform_users()

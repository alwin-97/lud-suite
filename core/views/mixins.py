"""Shared behaviour for admin CRUD views. Resource views stay explicit, thin
subclasses (see core/views/configuration.py) so each one is easy to grep."""
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, UpdateView

from core.permissions import AdminRequiredMixin


class AdminFormMixin(AdminRequiredMixin):
    """Create/update page rendered by core/admin/form.html.

    Subclasses set model, form_class and list_url_name; page copy comes from
    eyebrow / description / submit_label / form_layout ("stack" or "grid").
    """

    template_name = "core/admin/form.html"
    list_url_name = None
    eyebrow = "Configuration"
    description = ""
    submit_label = "Save"
    form_layout = "stack"
    title_verb = ""
    success_verb = ""
    success_message = ""

    def verbose_name(self):
        return self.model._meta.verbose_name

    def get_title(self):
        return f"{self.title_verb} {self.verbose_name()}"

    def get_success_url(self):
        return reverse(self.list_url_name)

    def get_success_message(self):
        return self.success_message or (
            f"{self.verbose_name().capitalize()} {self.success_verb} successfully."
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        from core.models import ChangeHistory, Cohort, log_change
        action = (
            ChangeHistory.Action.CREATE
            if self.title_verb == "Add"
            else ChangeHistory.Action.UPDATE
        )
        cohort = self.object if isinstance(self.object, Cohort) else getattr(self.object, "cohort", None)
        log_change(
            actor=self.request.user,
            action=action,
            entity_type=self.verbose_name().capitalize(),
            entity_name=str(self.object),
            entity_id=getattr(self.object, "pk", None),
            cohort=cohort,
            description=self.get_success_message(),
        )
        messages.success(self.request, self.get_success_message())
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=self.get_title(),
            eyebrow=self.eyebrow,
            description=self.description,
            submit_label=self.submit_label,
            form_layout=self.form_layout,
            cancel_url=reverse(self.list_url_name),
        )
        return context


class AdminCreateView(AdminFormMixin, CreateView):
    title_verb = "Add"
    success_verb = "created"


class AdminUpdateView(AdminFormMixin, UpdateView):
    title_verb = "Edit"
    success_verb = "updated"


class AdminDeleteView(AdminRequiredMixin, DeleteView):
    """POST-only delete. A PROTECT foreign key shows protected_message instead."""

    http_method_names = ["post"]
    list_url_name = None
    protected_message = ""

    def get_success_url(self):
        return reverse(self.list_url_name)

    def form_valid(self, form):
        verbose = self.model._meta.verbose_name
        from core.models import ChangeHistory, log_change
        try:
            name = str(self.object)
            pk = self.object.pk
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                self.protected_message or f"This {verbose} is in use. Deactivate it instead.",
            )
        else:
            log_change(
                actor=self.request.user,
                action=ChangeHistory.Action.DELETE,
                entity_type=verbose.capitalize(),
                entity_name=name,
                entity_id=pk,
                description=f"{verbose.capitalize()} '{name}' deleted.",
            )
            messages.success(self.request, f"{verbose.capitalize()} deleted successfully.")
        return redirect(self.get_success_url())

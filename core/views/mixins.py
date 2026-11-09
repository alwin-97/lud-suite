"""Shared behaviour for admin CRUD views. Resource views stay explicit, thin
subclasses (see core/views/configuration.py) so each one is easy to grep."""
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
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

    def supports_members(self):
        return self.model._meta.model_name in {"program", "location", "chapter", "cohort"}

    def get_members_form(self):
        if not hasattr(self, "members_form"):
            from core.forms.memberships import ResourceMembersForm
            self.members_form = ResourceMembersForm(
                self.request.POST if self.request.method == "POST" and self.request.POST.get("members_present") == "1" else None,
                prefix="members", scope=getattr(self, "object", None),
            )
        return self.members_form

    def is_drawer_request(self):
        return (
            self.model._meta.model_name in {"program", "location", "chapter", "cohort"}
            and self.request.headers.get("X-Form-Drawer") == "true"
        )

    def get_template_names(self):
        if self.is_drawer_request():
            return ["components/forms/drawer_form.html"]
        return super().get_template_names()

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

    @transaction.atomic
    def form_valid(self, form):
        before, before_scopes = {}, {}
        if self.supports_members():
            from core.services.audit import configuration_values, scope_ids
            previous = self.model.objects.filter(pk=form.instance.pk).first()
            if previous:
                before = configuration_values(previous, form._meta.fields)
                before_scopes = scope_ids(previous)
        members_form = self.get_members_form() if self.supports_members() else None
        if members_form and members_form.is_bound and not members_form.is_valid():
            return self.form_invalid(form)
        response = super().form_valid(form)
        if members_form and members_form.is_bound:
            members_form.save(self.object, self.request.user)
        if self.supports_members():
            from core.services.resources import add_resource
            for upload in form.cleaned_data.get("resource_files", []):
                add_resource(self.object, upload, self.request.user)
        from core.models import ChangeHistory, Cohort, log_change
        action = (
            ChangeHistory.Action.CREATE
            if self.title_verb == "Add"
            else ChangeHistory.Action.UPDATE
        )
        cohort = self.object if isinstance(self.object, Cohort) else getattr(self.object, "cohort", None)
        audit_details = {}
        if self.supports_members():
            after = configuration_values(self.object, form._meta.fields)
            audit_details = {
                "changes": {name: {"before": before.get(name), "after": value}
                            for name, value in after.items() if before.get(name) != value},
                "scope_ids": scope_ids(self.object), "before_scope_ids": before_scopes,
            }
        log_change(
            actor=self.request.user,
            action=action,
            entity_type=self.verbose_name().capitalize(),
            entity_name=str(self.object),
            entity_id=getattr(self.object, "pk", None),
            cohort=cohort,
            description=self.get_success_message(),
            details=audit_details,
        )
        messages.success(self.request, self.get_success_message())
        if self.is_drawer_request():
            return JsonResponse({"saved": True})
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
        if self.supports_members():
            from core.models import ChangeHistory
            context["members_form"] = self.get_members_form()
            if getattr(self, "object", None):
                history = ChangeHistory.objects.filter(entity_type="Member")
                if self.model._meta.model_name == "cohort":
                    history = history.filter(cohort=self.object)
                else:
                    history = history.filter(details__scope_type=self.model._meta.model_name,
                                             details__scope_id=self.object.pk)
                context["member_history"] = history.select_related("actor")[:20]
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
        audit_details = {}
        if self.model._meta.model_name in {"program", "location", "chapter", "cohort"}:
            from core.services.audit import scope_ids
            audit_details = {"scope_ids": scope_ids(self.object)}
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
                details=audit_details,
            )
            messages.success(self.request, f"{verbose.capitalize()} deleted successfully.")
        return redirect(self.get_success_url())

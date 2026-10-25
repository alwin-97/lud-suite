from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from core.forms import (
    ChapterForm,
    CohortActivityForm,
    CohortForm,
    CohortMemberForm,
    CohortMemberReallocateForm,
    LocationForm,
    MentorAssignmentForm,
    ProgramForm,
    TermForm,
    TermResourceForm,
)
from core.models import (
    ChangeHistory,
    Chapter,
    Cohort,
    CohortActivity,
    CohortMembership,
    Location,
    MentorAssignment,
    Program,
    RolePermission,
    Term,
    TermResource,
    log_change,
)
from core.permissions import (
    DEFAULT_ROLE_PERMISSIONS,
    AdminRequiredMixin,
    RoleAccessRequiredMixin,
    has_role_permission,
)
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
            role_count=len(CohortMembership.ROLE_CHOICES),
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


class CohortManageView(RoleAccessRequiredMixin, DetailView):
    """One cohort and its members: add a role, switch it on/off, or remove it."""

    queryset = Cohort.objects.select_related(
        "chapter", "chapter__location", "chapter__location__program"
    )
    pk_url_kwarg = "cohort_id"
    template_name = "core/admin/configuration/cohort_manage.html"
    context_object_name = "cohort"
    permission_resource = "cohorts"
    permission_action = "read"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not has_role_permission(request.user, "members", "create", cohort=self.object):
            raise PermissionDenied("You do not have permission to allocate members to this cohort.")
        form = CohortMemberForm(request.POST, cohort=self.object)
        if form.is_valid():
            membership = form.save()
            log_change(
                actor=request.user,
                action=ChangeHistory.Action.ALLOCATE,
                entity_type="Member",
                entity_name=f"{membership.user} ({membership.get_role_display()})",
                entity_id=membership.pk,
                cohort=self.object,
                description=f"Allocated {membership.get_role_display()} role to {membership.user} in {self.object.name}.",
                details={"user": membership.user.email, "role": membership.role},
            )
            messages.success(
                request,
                f"{membership.user} allocated as {membership.get_role_display()}.",
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
        context["terms"] = list(
            self.object.terms.prefetch_related("resources", "activities").order_by("sequence", "start_date")
        )
        context["activities"] = list(
            self.object.activities.select_related("term").order_by("term__sequence", "sequence", "start_date")
        )
        context["history"] = list(
            self.object.change_history.select_related("actor")[:25]
        )
        context["mentor_assignments"] = list(
            self.object.mentor_assignments.filter(is_active=True).select_related("mentor", "mentee", "assigned_by")
        )
        context["mentor_assignment_form"] = MentorAssignmentForm(cohort=self.object)
        return context


class CohortMemberActionView(RoleAccessRequiredMixin, View):
    """POST-only: action is "toggle" (activate/deactivate) or "remove"."""

    http_method_names = ["post"]
    action = ""
    permission_resource = "members"

    def dispatch(self, request, *args, **kwargs):
        self.permission_action = "delete" if self.action == "remove" else "update"
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, cohort_id, membership_id):
        membership = get_object_or_404(
            CohortMembership.objects.select_related("user", "cohort"),
            pk=membership_id,
            cohort_id=cohort_id,
        )
        if self.action == "remove":
            log_change(
                actor=request.user,
                action=ChangeHistory.Action.REMOVE,
                entity_type="Member",
                entity_name=f"{membership.user} ({membership.get_role_display()})",
                entity_id=membership.pk,
                cohort=membership.cohort,
                description=f"Removed {membership.get_role_display()} role from {membership.user}.",
            )
            membership.delete()
            messages.success(request, f"{membership.user}'s {membership.get_role_display()} role removed.")
        else:
            membership.is_active = not membership.is_active
            membership.save(update_fields=["is_active"])
            action = ChangeHistory.Action.ACTIVATE if membership.is_active else ChangeHistory.Action.DEACTIVATE
            state = "activated" if membership.is_active else "deactivated"
            log_change(
                actor=request.user,
                action=action,
                entity_type="Member",
                entity_name=f"{membership.user} ({membership.get_role_display()})",
                entity_id=membership.pk,
                cohort=membership.cohort,
                description=f"{state.capitalize()} {membership.get_role_display()} role for {membership.user}.",
                details={"user": membership.user.email, "is_active": membership.is_active},
            )
            messages.success(request, f"{membership.user}'s {membership.get_role_display()} role {state}.")
        return redirect(reverse("cohort_manage", args=[cohort_id]))


# Cohort Terms -------------------------------------------------------------

class CohortTermCreateView(RoleAccessRequiredMixin, CreateView):
    model = Term
    form_class = TermForm
    template_name = "core/admin/form.html"
    permission_resource = "terms"
    permission_action = "create"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(
            Cohort.objects.select_related("chapter", "chapter__location", "chapter__location__program"),
            pk=kwargs["cohort_id"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["cohort"] = self.cohort
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.CREATE,
            entity_type="Term",
            entity_name=self.object.name,
            entity_id=self.object.pk,
            cohort=self.cohort,
            description=f"Created {self.object.name} (Sequence {self.object.sequence}) with {self.object.resources.count()} attached resource(s).",
            details={
                "sequence": self.object.sequence,
                "start_date": str(self.object.start_date) if self.object.start_date else None,
                "end_date": str(self.object.end_date) if self.object.end_date else None,
                "resource_count": self.object.resources.count(),
            },
        )
        messages.success(self.request, f"Term '{self.object.name}' created with attached resources.")
        return response

    def get_success_url(self):
        return reverse("cohort_term_detail", args=[self.cohort.pk, self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=f"Add term to {self.cohort.name}",
            eyebrow=f"{self.cohort.chapter.location.program.name} · {self.cohort.name}",
            description="Create a term and attach documents, images, and external resource URLs.",
            submit_label="Create term",
            form_layout="grid",
            cancel_url=reverse("cohort_manage", args=[self.cohort.pk]),
        )
        return context


class CohortTermUpdateView(RoleAccessRequiredMixin, UpdateView):
    model = Term
    form_class = TermForm
    pk_url_kwarg = "term_id"
    template_name = "core/admin/form.html"
    permission_resource = "terms"
    permission_action = "update"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(
            Cohort.objects.select_related("chapter", "chapter__location", "chapter__location__program"),
            pk=kwargs["cohort_id"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Term.objects.filter(cohort=self.cohort)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["cohort"] = self.cohort
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.UPDATE,
            entity_type="Term",
            entity_name=self.object.name,
            entity_id=self.object.pk,
            cohort=self.cohort,
            description=f"Updated details for term '{self.object.name}'.",
            details={
                "sequence": self.object.sequence,
                "start_date": str(self.object.start_date) if self.object.start_date else None,
                "end_date": str(self.object.end_date) if self.object.end_date else None,
                "is_active": self.object.is_active,
            },
        )
        messages.success(self.request, f"Term '{self.object.name}' updated successfully.")
        return response

    def get_success_url(self):
        return reverse("cohort_term_detail", args=[self.cohort.pk, self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=f"Edit {self.object.name}",
            eyebrow=f"{self.cohort.name} · Terms",
            description="Update term dates or attach additional documents, images, and links.",
            submit_label="Update term",
            form_layout="grid",
            cancel_url=reverse("cohort_term_detail", args=[self.cohort.pk, self.object.pk]),
        )
        return context


class CohortTermDetailView(RoleAccessRequiredMixin, DetailView):
    """View term details and manage its resources (documents, images, links)."""

    model = Term
    pk_url_kwarg = "term_id"
    template_name = "core/admin/configuration/term_detail.html"
    context_object_name = "term"
    permission_resource = "terms"
    permission_action = "read"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(
            Cohort.objects.select_related("chapter", "chapter__location", "chapter__location__program"),
            pk=kwargs["cohort_id"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Term.objects.filter(cohort=self.cohort).prefetch_related(
            "resources", "activities", "tasks", "questions"
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not has_role_permission(request.user, "resources", "create", cohort=self.cohort):
            raise PermissionDenied("You do not have permission to add resources to this term.")
        form = TermResourceForm(request.POST, request.FILES, term=self.object)
        if form.is_valid():
            resource = form.save()
            action = ChangeHistory.Action.UPLOAD if resource.file else ChangeHistory.Action.CREATE
            log_change(
                actor=request.user,
                action=action,
                entity_type="Resource",
                entity_name=resource.title,
                entity_id=resource.pk,
                cohort=self.cohort,
                description=f"Attached {resource.get_resource_type_display()} '{resource.title}' to {self.object.name}.",
                details={
                    "term": self.object.name,
                    "resource_type": resource.resource_type,
                    "url": resource.url or (resource.file.name if resource.file else ""),
                },
            )
            messages.success(
                request,
                f"{resource.get_resource_type_display()} '{resource.title}' added successfully.",
            )
            return redirect("cohort_term_detail", cohort_id=self.cohort.pk, term_id=self.object.pk)
        return self.render_to_response(self.get_context_data(resource_form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resources = list(self.object.resources.all())
        context["cohort"] = self.cohort
        context["resources"] = resources
        context["documents"] = [r for r in resources if r.is_document]
        context["images"] = [r for r in resources if r.is_image]
        context["links"] = [r for r in resources if r.is_link]
        context["activities"] = list(self.object.activities.all().order_by("sequence", "start_date"))
        context["tasks"] = list(self.object.tasks.all().order_by("sequence", "due_date"))
        context["questions"] = list(self.object.questions.all().order_by("sequence", "due_date"))
        context["can_manage_tasks"] = has_role_permission(
            self.request.user, "tasks", "create", cohort=self.cohort
        )
        context["can_manage_questions"] = has_role_permission(
            self.request.user, "questions", "create", cohort=self.cohort
        )
        context["history"] = list(
            self.cohort.change_history.filter(
                Q(entity_name__icontains=self.object.name) | Q(description__icontains=self.object.name)
            ).select_related("actor")[:15]
        )
        context["resource_form"] = kwargs.get("resource_form") or TermResourceForm(term=self.object)
        return context


class CohortTermDeleteView(RoleAccessRequiredMixin, DeleteView):
    model = Term
    pk_url_kwarg = "term_id"
    http_method_names = ["post"]
    permission_resource = "terms"
    permission_action = "delete"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(Cohort, pk=kwargs["cohort_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Term.objects.filter(cohort=self.cohort)

    def form_valid(self, form):
        term_name = self.object.name
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.DELETE,
            entity_type="Term",
            entity_name=term_name,
            entity_id=self.object.pk,
            cohort=self.cohort,
            description=f"Deleted term '{term_name}' and all its attached resources.",
        )
        self.object.delete()
        messages.success(self.request, f"Term '{term_name}' and all its resources deleted successfully.")
        return redirect("cohort_manage", cohort_id=self.cohort.pk)


class CohortTermResourceDeleteView(RoleAccessRequiredMixin, View):
    http_method_names = ["post"]
    permission_resource = "resources"
    permission_action = "delete"

    def post(self, request, cohort_id, term_id, resource_id):
        resource = get_object_or_404(
            TermResource.objects.select_related("term", "term__cohort"),
            pk=resource_id,
            term_id=term_id,
            term__cohort_id=cohort_id,
        )
        title = resource.title
        res_type = resource.get_resource_type_display()
        term_name = resource.term.name
        cohort = resource.term.cohort
        resource.delete()
        log_change(
            actor=request.user,
            action=ChangeHistory.Action.REMOVE,
            entity_type="Resource",
            entity_name=title,
            entity_id=resource_id,
            cohort=cohort,
            description=f"Removed {res_type} '{title}' from {term_name}.",
        )
        messages.success(request, f"Resource '{title}' removed.")
        return redirect("cohort_term_detail", cohort_id=cohort_id, term_id=term_id)


# Member Reallocation ------------------------------------------------------

class CohortMemberReallocateView(RoleAccessRequiredMixin, DetailView):
    """Reallocate member role or transfer to another cohort."""

    model = CohortMembership
    pk_url_kwarg = "membership_id"
    template_name = "core/admin/form.html"
    permission_resource = "members"
    permission_action = "update"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(Cohort, pk=kwargs["cohort_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return CohortMembership.objects.filter(cohort=self.cohort).select_related("user", "cohort")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        membership = self.object
        context.update(
            title=f"Reallocate {membership.user}",
            eyebrow=f"{self.cohort.name} · Member Management",
            description=f"Current role: {membership.get_role_display()}. Change their role or transfer them to another active cohort.",
            submit_label="Save reallocation",
            form=kwargs.get("form") or CohortMemberReallocateForm(instance=membership),
            form_layout="stack",
            cancel_url=reverse("cohort_manage", args=[self.cohort.pk]),
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        membership = self.object
        form = CohortMemberReallocateForm(request.POST, instance=membership)
        if form.is_valid():
            old_role_display = membership.get_role_display()
            target_cohort = form.cleaned_data.get("target_cohort") or self.cohort
            new_role = form.cleaned_data.get("role")

            if target_cohort.pk != self.cohort.pk:
                new_membership, _ = CohortMembership.objects.update_or_create(
                    user=membership.user,
                    cohort=target_cohort,
                    role=new_role,
                    defaults={"is_active": True},
                )
                membership.delete()
                log_change(
                    actor=request.user,
                    action=ChangeHistory.Action.REALLOCATE,
                    entity_type="Member",
                    entity_name=f"{membership.user} ({new_membership.get_role_display()})",
                    entity_id=new_membership.pk,
                    cohort=target_cohort,
                    description=f"Reallocated {membership.user} from {self.cohort.name} ({old_role_display}) to {target_cohort.name} ({new_membership.get_role_display()}).",
                    details={
                        "from_cohort": self.cohort.name,
                        "to_cohort": target_cohort.name,
                        "new_role": new_role,
                    },
                )
                messages.success(
                    request,
                    f"{membership.user} reallocated to {target_cohort.name} as {new_membership.get_role_display()}.",
                )
            else:
                membership.role = new_role
                membership.save(update_fields=["role"])
                log_change(
                    actor=request.user,
                    action=ChangeHistory.Action.REALLOCATE,
                    entity_type="Member",
                    entity_name=f"{membership.user} ({membership.get_role_display()})",
                    entity_id=membership.pk,
                    cohort=self.cohort,
                    description=f"Reallocated {membership.user} from {old_role_display} to {membership.get_role_display()} in {self.cohort.name}.",
                    details={"cohort": self.cohort.name, "new_role": new_role},
                )
                messages.success(
                    request,
                    f"{membership.user} reallocated as {membership.get_role_display()}.",
                )
            return redirect("cohort_manage", cohort_id=self.cohort.pk)
        return self.render_to_response(self.get_context_data(form=form))


class CohortMentorAllocateView(RoleAccessRequiredMixin, View):
    """Allocate a mentee to a mentor within the cohort."""

    http_method_names = ["post"]
    permission_resource = "members"
    permission_action = "update"

    def post(self, request, cohort_id):
        cohort = get_object_or_404(Cohort, pk=cohort_id)
        form = MentorAssignmentForm(request.POST, cohort=cohort)
        if form.is_valid():
            mentor = form.cleaned_data["mentor"]
            mentee = form.cleaned_data["mentee"]
            notes = form.cleaned_data.get("notes", "")

            assignment, created = MentorAssignment.objects.update_or_create(
                cohort=cohort,
                mentor=mentor,
                mentee=mentee,
                defaults={"is_active": True, "notes": notes, "assigned_by": request.user},
            )
            action_desc = "Allocated" if created else "Updated allocation for"
            log_change(
                actor=request.user,
                action=ChangeHistory.Action.ALLOCATE,
                entity_type="MentorAssignment",
                entity_name=f"{mentor} -> {mentee}",
                entity_id=assignment.pk,
                cohort=cohort,
                description=f"{action_desc} mentee {mentee.get_full_name() or mentee.email} to mentor {mentor.get_full_name() or mentor.email} in {cohort.name}.",
                details={"mentor": mentor.email, "mentee": mentee.email, "notes": notes},
            )
            messages.success(
                request,
                f"Mentee {mentee.get_full_name() or mentee.email} allocated to mentor {mentor.get_full_name() or mentor.email}.",
            )
        else:
            errors = "; ".join([f"{f}: {e[0]}" for f, e in form.errors.items()])
            messages.error(request, f"Failed to allocate mentor: {errors}")

        return redirect("cohort_manage", cohort_id=cohort_id)


class CohortMentorUnassignView(RoleAccessRequiredMixin, View):
    """Remove / deallocate a mentor-mentee pairing."""

    http_method_names = ["post"]
    permission_resource = "members"
    permission_action = "update"

    def post(self, request, cohort_id, assignment_id):
        assignment = get_object_or_404(
            MentorAssignment.objects.select_related("cohort", "mentor", "mentee"),
            pk=assignment_id,
            cohort_id=cohort_id,
        )
        mentor_name = assignment.mentor.get_full_name() or assignment.mentor.email
        mentee_name = assignment.mentee.get_full_name() or assignment.mentee.email
        cohort = assignment.cohort

        log_change(
            actor=request.user,
            action=ChangeHistory.Action.REMOVE,
            entity_type="MentorAssignment",
            entity_name=f"{assignment.mentor} -> {assignment.mentee}",
            entity_id=assignment.pk,
            cohort=cohort,
            description=f"Removed mentorship pairing of {mentee_name} under mentor {mentor_name} in {cohort.name}.",
        )
        assignment.delete()
        messages.success(request, f"Removed mentorship pairing of {mentee_name} from {mentor_name}.")
        return redirect("cohort_manage", cohort_id=cohort_id)


# Cohort Activity Timeline Planning ----------------------------------------

class CohortTimelineView(RoleAccessRequiredMixin, DetailView):
    """Complete activity timeline for the cohort spread across multiple terms."""

    model = Cohort
    pk_url_kwarg = "cohort_id"
    template_name = "core/admin/configuration/cohort_timeline.html"
    context_object_name = "cohort"
    permission_resource = "activities"
    permission_action = "read"

    def get_queryset(self):
        return Cohort.objects.select_related(
            "chapter", "chapter__location", "chapter__location__program"
        ).prefetch_related(
            "terms",
            "activities__term",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        terms = list(
            self.object.terms.prefetch_related("activities").order_by("sequence", "start_date")
        )
        activities = list(
            self.object.activities.select_related("term").order_by(
                "term__sequence", "sequence", "start_date"
            )
        )
        total = len(activities)
        completed = sum(1 for a in activities if a.status == CohortActivity.Status.COMPLETED)
        in_progress = sum(1 for a in activities if a.status == CohortActivity.Status.IN_PROGRESS)
        planned = sum(1 for a in activities if a.status == CohortActivity.Status.PLANNED)
        delayed = sum(1 for a in activities if a.status == CohortActivity.Status.DELAYED)

        context.update(
            terms=terms,
            activities=activities,
            total_activities=total,
            completed_count=completed,
            in_progress_count=in_progress,
            planned_count=planned,
            delayed_count=delayed,
            progress_percent=round((completed / total * 100)) if total else 0,
        )
        return context


class CohortActivityCreateView(RoleAccessRequiredMixin, CreateView):
    """Add a planned activity to a term in the cohort's timeline."""

    model = CohortActivity
    form_class = CohortActivityForm
    template_name = "core/admin/form.html"
    permission_resource = "activities"
    permission_action = "create"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(
            Cohort.objects.select_related("chapter", "chapter__location", "chapter__location__program"),
            pk=kwargs["cohort_id"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["cohort"] = self.cohort
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.CREATE,
            entity_type="Activity",
            entity_name=self.object.title,
            entity_id=self.object.pk,
            cohort=self.cohort,
            description=f"Planned activity '{self.object.title}' for {self.object.term.name} ({self.object.get_target_audience_display()}).",
            details={
                "term": self.object.term.name,
                "status": self.object.status,
                "target_audience": self.object.target_audience,
                "start_date": str(self.object.start_date) if self.object.start_date else None,
                "end_date": str(self.object.end_date) if self.object.end_date else None,
            },
        )
        messages.success(
            self.request,
            f"Activity '{self.object.title}' planned for {self.object.term.name}.",
        )
        return response

    def get_success_url(self):
        return reverse("cohort_timeline", args=[self.cohort.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=f"Plan activity for {self.cohort.name}",
            eyebrow="Timeline Planning",
            description="Schedule an activity or milestone within a term, specifying dates, status, and participating member format.",
            submit_label="Save activity plan",
            form_layout="grid",
            cancel_url=reverse("cohort_timeline", args=[self.cohort.pk]),
        )
        return context


class CohortActivityUpdateView(RoleAccessRequiredMixin, UpdateView):
    model = CohortActivity
    form_class = CohortActivityForm
    pk_url_kwarg = "activity_id"
    template_name = "core/admin/form.html"
    permission_resource = "activities"
    permission_action = "update"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(Cohort, pk=kwargs["cohort_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return CohortActivity.objects.filter(cohort=self.cohort)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["cohort"] = self.cohort
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.UPDATE,
            entity_type="Activity",
            entity_name=self.object.title,
            entity_id=self.object.pk,
            cohort=self.cohort,
            description=f"Updated activity '{self.object.title}' in {self.object.term.name} (Status: {self.object.get_status_display()}).",
            details={
                "status": self.object.status,
                "target_audience": self.object.target_audience,
                "start_date": str(self.object.start_date) if self.object.start_date else None,
                "end_date": str(self.object.end_date) if self.object.end_date else None,
            },
        )
        messages.success(self.request, f"Activity '{self.object.title}' updated successfully.")
        return response

    def get_success_url(self):
        return reverse("cohort_timeline", args=[self.cohort.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            title=f"Edit activity: {self.object.title}",
            eyebrow=f"{self.cohort.name} · {self.object.term.name}",
            description="Update schedule, progress status, or participating member group.",
            submit_label="Update activity",
            form_layout="grid",
            cancel_url=reverse("cohort_timeline", args=[self.cohort.pk]),
        )
        return context


class CohortActivityDeleteView(RoleAccessRequiredMixin, DeleteView):
    model = CohortActivity
    pk_url_kwarg = "activity_id"
    http_method_names = ["post"]
    permission_resource = "activities"
    permission_action = "delete"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(Cohort, pk=kwargs["cohort_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return CohortActivity.objects.filter(cohort=self.cohort)

    def form_valid(self, form):
        title = self.object.title
        term_name = self.object.term.name
        self.object.delete()
        log_change(
            actor=self.request.user,
            action=ChangeHistory.Action.DELETE,
            entity_type="Activity",
            entity_name=title,
            entity_id=self.object.pk,
            cohort=self.cohort,
            description=f"Removed planned activity '{title}' from {term_name}.",
        )
        messages.success(self.request, f"Activity '{title}' deleted.")
        return redirect("cohort_timeline", cohort_id=self.cohort.pk)


# Central Audit Trail & Review ---------------------------------------------

class AuditTrailReviewView(RoleAccessRequiredMixin, ListView):
    """Central audit trail for logs and review across all stages."""

    model = ChangeHistory
    template_name = "core/admin/audit_log.html"
    context_object_name = "history_entries"
    paginate_by = 50
    permission_resource = "audit_log"
    permission_action = "read"

    def get_queryset(self):
        qs = ChangeHistory.objects.select_related(
            "actor", "cohort", "cohort__chapter"
        ).order_by("-created_at")

        # Non-platform admins only view logs for cohorts they actively belong to
        if not getattr(self.request.user, "is_platform_admin", False):
            user_cohort_ids = self.request.user.cohort_memberships.filter(
                is_active=True
            ).values_list("cohort_id", flat=True)
            qs = qs.filter(cohort_id__in=user_cohort_ids)

        action = self.request.GET.get("action", "").strip()
        if action:
            qs = qs.filter(action=action)
        entity = self.request.GET.get("entity", "").strip()
        if entity:
            qs = qs.filter(entity_type=entity)
        cohort_id = self.request.GET.get("cohort", "").strip()
        if cohort_id:
            qs = qs.filter(cohort_id=cohort_id)
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(description__icontains=query)
                | Q(entity_name__icontains=query)
                | Q(actor__email__icontains=query)
                | Q(actor__first_name__icontains=query)
                | Q(actor__last_name__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cohort_filter = {}
        if not getattr(self.request.user, "is_platform_admin", False):
            cohort_filter["memberships__user"] = self.request.user
            cohort_filter["memberships__is_active"] = True

        context.update(
            actions=ChangeHistory.Action.choices,
            entity_types=[
                "Cohort",
                "Term",
                "Resource",
                "Member",
                "Activity",
                "Program",
                "Location",
                "Chapter",
                "User",
                "Permission",
                "RolePermission",
            ],
            cohorts=Cohort.objects.filter(is_active=True, **cohort_filter).distinct().order_by("name"),
            selected_action=self.request.GET.get("action", ""),
            selected_entity=self.request.GET.get("entity", ""),
            selected_cohort=self.request.GET.get("cohort", ""),
            search_query=self.request.GET.get("q", ""),
            total_logs=self.get_queryset().count(),
        )
        return context


# Role-based Access Control Matrix -----------------------------------------

class RolePermissionMatrixView(AdminRequiredMixin, TemplateView):
    """Configuration view for the Role-Based Access Control (RBAC) permissions matrix."""

    template_name = "core/admin/configuration/permissions_matrix.html"

    RESOURCE_DESCRIPTIONS = {
        RolePermission.Resource.TERMS: "Create, view, update schedule, and delete terms within a cohort.",
        RolePermission.Resource.RESOURCES: "Upload syllabus/documents, images, attach external resource URLs, and remove files.",
        RolePermission.Resource.ACTIVITIES: "Schedule milestones, view timeline progress, update activity status, and remove activities.",
        RolePermission.Resource.MEMBERS: "Allocate members, change roles (Mentee, Mentor, Senior Member, Leader), transfer between cohorts, activate/deactivate.",
        RolePermission.Resource.COHORTS: "View and manage cohort profile, curriculum overview, and metadata.",
        RolePermission.Resource.AUDIT_LOG: "Review platform and cohort compliance audit trails and chronological change history.",
        RolePermission.Resource.REPORTS: "Prepare, view, submit, review, and evaluate participant activity reports and reflections.",
    }

    def get_matrix_data(self):
        db_perms = {
            (p.role, p.resource): p
            for p in RolePermission.objects.all()
        }

        roles_data = []
        custom_count = len(db_perms)

        for role_code, role_label in CohortMembership.ROLE_CHOICES:
            resources_data = []
            for res_code, res_label in RolePermission.Resource.choices:
                perm_obj = db_perms.get((role_code, res_code))
                if perm_obj:
                    can_create = perm_obj.can_create
                    can_read = perm_obj.can_read
                    can_update = perm_obj.can_update
                    can_delete = perm_obj.can_delete
                    is_custom = True
                else:
                    default = DEFAULT_ROLE_PERMISSIONS.get(role_code, {}).get(res_code, {})
                    can_create = default.get("create", False)
                    can_read = default.get("read", False)
                    can_update = default.get("update", False)
                    can_delete = default.get("delete", False)
                    is_custom = False

                resources_data.append({
                    "code": res_code,
                    "label": res_label,
                    "description": self.RESOURCE_DESCRIPTIONS.get(res_code, ""),
                    "can_create": can_create,
                    "can_read": can_read,
                    "can_update": can_update,
                    "can_delete": can_delete,
                    "is_custom": is_custom,
                })

            roles_data.append({
                "code": role_code,
                "label": role_label,
                "resources": resources_data,
            })

        return roles_data, custom_count

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        roles_data, custom_count = self.get_matrix_data()
        context.update(
            roles_matrix=roles_data,
            custom_overrides_count=custom_count,
            total_rules_count=len(CohortMembership.ROLE_CHOICES) * len(RolePermission.Resource.choices),
            resource_choices=RolePermission.Resource.choices,
        )
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get("action") == "reset_defaults":
            deleted_count, _ = RolePermission.objects.all().delete()
            log_change(
                actor=request.user,
                action=ChangeHistory.Action.UPDATE,
                entity_type="RolePermission",
                entity_name="All Roles",
                description="Reset all role-based permissions matrix to platform system defaults.",
                details={"cleared_overrides": deleted_count},
            )
            messages.success(request, "All role permissions have been reset to platform system defaults.")
            return redirect("role_permissions_matrix")

        saved_count = 0
        for role_code, _ in CohortMembership.ROLE_CHOICES:
            for res_code, _ in RolePermission.Resource.choices:
                can_create = f"perm_{role_code}_{res_code}_create" in request.POST
                can_read = f"perm_{role_code}_{res_code}_read" in request.POST
                can_update = f"perm_{role_code}_{res_code}_update" in request.POST
                can_delete = f"perm_{role_code}_{res_code}_delete" in request.POST

                RolePermission.objects.update_or_create(
                    role=role_code,
                    resource=res_code,
                    defaults={
                        "can_create": can_create,
                        "can_read": can_read,
                        "can_update": can_update,
                        "can_delete": can_delete,
                    },
                )
                saved_count += 1

        log_change(
            actor=request.user,
            action=ChangeHistory.Action.UPDATE,
            entity_type="RolePermission",
            entity_name="Permissions Matrix",
            description=f"Saved role-based access control matrix ({saved_count} resource rules updated across {len(CohortMembership.ROLE_CHOICES)} roles).",
            details={"saved_rules": saved_count},
        )
        messages.success(request, "Role permissions matrix saved successfully.")
        return redirect("role_permissions_matrix")




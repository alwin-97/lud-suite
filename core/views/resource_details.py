import json
import re

from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.views.generic import DetailView

from core.models import Chapter, ChangeHistory, Cohort, CohortMembership, Location, ScopeMembership
from core.permissions import AdminRequiredMixin


class ConfigurationDetailView(AdminRequiredMixin, DetailView):
    """Full configuration record, its descendants, memberships and audit history."""

    template_name = "core/admin/configuration/detail.html"
    resource_name = ""

    def get_queryset(self):
        queryset = super().get_queryset()
        relation = {"location": "program", "chapter": "location__program", "cohort": "chapter__location__program"}.get(self.resource_name)
        return queryset.select_related(relation) if relation else queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        kind = self.resource_name

        def paged(records, param, size=10):
            return Paginator(records, size).get_page(self.request.GET.get(param))
        locations = Location.objects.none()
        chapters = Chapter.objects.none()
        cohorts = Cohort.objects.none()
        if kind == "program":
            locations = Location.objects.filter(program=obj)
            chapters = Chapter.objects.filter(location__program=obj)
            cohorts = Cohort.objects.filter(chapter__location__program=obj)
        elif kind == "location":
            chapters = Chapter.objects.filter(location=obj)
            cohorts = Cohort.objects.filter(chapter__location=obj)
        elif kind == "chapter":
            cohorts = obj.cohorts.all()
        else:
            cohorts = Cohort.objects.filter(pk=obj.pk)
        locations = locations.select_related("program").order_by("name", "pk")
        chapters = chapters.select_related("location__program").order_by("name", "pk")
        cohorts = cohorts.select_related("chapter__location__program").order_by("-start_date", "name", "pk")

        # Include inactive and former members; membership rows are retained on departure.
        scope_filter = Q(pk__in=[])
        if kind != "cohort":
            scope_filter |= Q(**{kind: obj})
        scope_filter |= Q(location_id__in=locations.values("pk")) | Q(chapter_id__in=chapters.values("pk"))
        direct = ScopeMembership.objects.filter(scope_filter).select_related(
            "user", "program", "location__program", "chapter__location__program"
        )
        cohort_members = CohortMembership.objects.filter(cohort__in=cohorts).select_related("user", "cohort")
        members = []
        for membership in [*direct, *cohort_members]:
            scope = membership.cohort if isinstance(membership, CohortMembership) else membership.scope
            members.append({"membership": membership, "scope": scope,
                            "scope_type": scope._meta.verbose_name.capitalize(),
                            "scope_url": reverse(f"{scope._meta.model_name}_detail", args=[scope.pk])})
        members.sort(key=lambda row: (row["membership"].user.email, row["scope_type"], row["membership"].role))

        # Match stable IDs, never names, so equally named records stay separate.
        audit_filter = (
            Q(entity_type=kind.capitalize(), entity_id=obj.pk)
            | Q(**{f"details__scope_ids__{kind}": obj.pk})
            | Q(**{f"details__before_scope_ids__{kind}": obj.pk})
            | Q(details__scope_type=kind, details__scope_id=obj.pk)
            | Q(cohort__in=cohorts)
            | Q(entity_type="Location", entity_id__in=locations.values("pk"))
            | Q(entity_type="Chapter", entity_id__in=chapters.values("pk"))
            | Q(entity_type="Cohort", entity_id__in=cohorts.values("pk"))
            | Q(details__scope_type="location", details__scope_id__in=locations.values("pk"))
            | Q(details__scope_type="chapter", details__scope_id__in=chapters.values("pk"))
        )
        user_ids = {row["membership"].user_id for row in members}
        historical_users = ChangeHistory.objects.filter(audit_filter, entity_type="Member").values("details__user_id")
        audit_filter |= Q(entity_type="User", entity_id__in=user_ids) | Q(entity_type="User", entity_id__in=historical_users)
        logs = ChangeHistory.objects.filter(audit_filter).select_related("actor", "cohort").order_by("-created_at", "-pk")
        total_logs = logs.count()
        query = self.request.GET.get("q", "").strip()
        action = self.request.GET.get("action", "").strip()
        if query:
            logs = logs.filter(Q(description__icontains=query) | Q(entity_name__icontains=query)
                               | Q(actor__email__icontains=query) | Q(actor__first_name__icontains=query)
                               | Q(actor__last_name__icontains=query))
        if action:
            logs = logs.filter(action=action)
        page = Paginator(logs, 25).get_page(self.request.GET.get("page"))
        for entry in page:
            entry.field_changes = [
                {"field": name.replace("_", " ").capitalize(), **values}
                for name, values in entry.details.get("changes", {}).items()
                if isinstance(values, dict) and "before" in values and "after" in values
            ] if isinstance(entry.details.get("changes"), dict) else []
            entry.formatted_details = json.dumps(entry.details, indent=2, ensure_ascii=False)

        ancestors = []
        if kind in {"location", "chapter", "cohort"}:
            chapter = obj.chapter if kind == "cohort" else obj if kind == "chapter" else None
            location = chapter.location if chapter else obj
            ancestors.append({"label": "Program", "object": location.program,
                              "url": reverse("program_detail", args=[location.program_id])})
            if chapter:
                ancestors.append({"label": "Location", "object": location,
                                  "url": reverse("location_detail", args=[location.pk])})
            if kind == "cohort":
                ancestors.append({"label": "Chapter", "object": chapter,
                                  "url": reverse("chapter_detail", args=[chapter.pk])})

        sections = []
        for label, name, records in (("Locations", "location", locations), ("Chapters", "chapter", chapters), ("Cohorts", "cohort", cohorts)):
            if name != kind and records.exists():
                rows_page = paged(records, f"{name}s_page")
                rows_page.object_list = [
                    {"object": item, "url": reverse(f"{name}_detail", args=[item.pk])} for item in rows_page
                ]
                sections.append({"title": label, "rows": rows_page, "param": f"{name}s_page",
                                 "anchor": f"structure-{name}"})

        section_params = {"members_page", "locations_page", "chapters_page", "cohorts_page",
                          "terms_page", "activities_page", "pairings_page"}
        # Retain section positions when changing audit filters.
        section_page_params = [(name, value) for name, value in self.request.GET.items()
                               if name in section_params or re.fullmatch(r"term_\d+_(resources|tasks|questions)_page", name)]
        reset_query = self.request.GET.copy()
        for name in ("q", "action", "page"):
            reset_query.pop(name, None)

        context.update(
            resource_library_url=reverse("scope_resources", args=[kind, obj.pk]),
            shared_resource_count=obj.shared_resources.filter(is_active=True).count(),
            resource=obj, resource_type=kind.capitalize(), ancestors=ancestors,
            list_url=reverse(f"{kind}_list"), edit_url=reverse(f"{kind}_edit", args=[obj.pk]),
            members=members, active_memberships=sum(row["membership"].is_active for row in members),
            members_page=paged(members, "members_page"),
            related_sections=sections, history_page=page, total_logs=total_logs,
            search_query=query, selected_action=action, actions=ChangeHistory.Action.choices,
            section_page_params=section_page_params,
            audit_reset_url=f"{self.request.path}?{reset_query.urlencode()}#audit",
            page_sections=[{"anchor": "overview", "label": "Overview"},
                           {"anchor": "members", "label": "Members"}]
                          + ([{"anchor": "structure", "label": "Structure"}] if sections else [])
                          + ([{"anchor": "curriculum", "label": "Terms and activities"}] if kind == "cohort" else [])
                          + [{"anchor": "audit", "label": "Audit logs and changes"}],
        )
        if kind == "cohort":
            terms = paged(obj.terms.order_by("sequence", "start_date", "name", "pk").prefetch_related("resources", "tasks", "questions"), "terms_page", 5)
            for term in terms:
                term.extra_content_open = False
                for relation in ("resources", "tasks", "questions"):
                    param = f"term_{term.pk}_{relation}_page"
                    setattr(term, f"{relation}_page", paged(getattr(term, relation).all(), param))
                    setattr(term, f"{relation}_page_param", param)
                    setattr(term, f"{relation}_anchor", f"term-{term.pk}-{relation}")
                    term.extra_content_open |= param in self.request.GET
            context.update(
                cohort=obj, terms=terms,
                activities=paged(obj.activities.select_related("term").order_by("term__sequence", "sequence", "start_date", "title", "pk"), "activities_page"),
                pairings=paged(obj.mentor_assignments.select_related("mentor", "mentee", "assigned_by").order_by("mentor__email", "mentee__email", "pk"), "pairings_page"),
            )
        return context

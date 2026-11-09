from pathlib import Path

from django.db.models import Q

from core.models import (
    ACTIVE_MEMBERSHIP_FILTER, Chapter, ChangeHistory, Cohort, Location, Program,
    RolePermission, ScopeResource, log_change,
)
from core.permissions import DEFAULT_ROLE_PERMISSIONS
from core.services.audit import scope_ids

SCOPE_MODELS = {"program": Program, "location": Location, "chapter": Chapter, "cohort": Cohort}
RESOURCE_RELATED = ("program", "location__program", "chapter__location__program",
                    "cohort__chapter__location__program", "uploaded_by")


def scope_key(scope):
    return f"{scope._meta.model_name}:{scope.pk}"


def scope_chain(scope):
    result = [scope]
    kind = scope._meta.model_name
    if kind == "cohort":
        scope = scope.chapter
        result.append(scope)
        kind = "chapter"
    if kind == "chapter":
        scope = scope.location
        result.append(scope)
        kind = "location"
    if kind == "location":
        result.append(scope.program)
    return result


def scope_label(scope):
    chain = list(reversed(scope_chain(scope)))
    return f"{scope._meta.verbose_name.capitalize()} · " + " / ".join(item.name for item in chain)


class ResourceAccess:
    """Read in one's active groups and ancestors; write only through a direct role."""

    def __init__(self, user):
        self.user = user
        self.admin = bool(user.is_authenticated and user.is_active and user.is_platform_admin)
        self.direct = {}
        self.readable = {}
        self.rules = {}
        if self.admin or not user.is_authenticated or not user.is_active:
            return
        self.rules = {rule.role: rule for rule in RolePermission.objects.filter(resource="resources")}
        memberships = user.scope_memberships.filter(is_active=True).select_related(
            "user", "program", "location__program", "chapter__location__program"
        )
        assignments = [(m.scope, m.role) for m in memberships if m.is_effectively_active]
        assignments += [(m.cohort, m.role) for m in user.cohort_memberships.filter(
            **ACTIVE_MEMBERSHIP_FILTER
        ).select_related("cohort__chapter__location__program")]
        for scope, role in assignments:
            self.direct.setdefault(scope_key(scope), {"scope": scope, "roles": set()})["roles"].add(role)
            if self.role_allows(role, "read"):
                for parent in scope_chain(scope):
                    self.readable[scope_key(parent)] = parent

    def role_allows(self, role, action):
        rule = self.rules.get(role)
        return bool(getattr(rule, f"can_{action}", False)) if rule else DEFAULT_ROLE_PERMISSIONS.get(role, {}).get("resources", {}).get(action, False)

    def allows(self, scope, action="read"):
        if self.admin:
            return True
        if not self.user.is_authenticated or not self.user.is_active:
            return False
        if action == "read":
            return scope_key(scope) in self.readable
        direct = self.direct.get(scope_key(scope))
        return bool(direct and any(self.role_allows(role, action) for role in direct["roles"]))

    def scopes(self, action="read"):
        if self.admin:
            result = []
            for kind, model in SCOPE_MODELS.items():
                relation = {"location": "program", "chapter": "location__program", "cohort": "chapter__location__program"}.get(kind)
                queryset = model.objects.all()
                result.extend(queryset.select_related(relation) if relation else queryset)
        elif action == "read":
            result = list(self.readable.values())
        else:
            result = [entry["scope"] for entry in self.direct.values() if self.allows(entry["scope"], action)]
        return sorted(result, key=lambda scope: scope_label(scope).casefold())

    def query(self):
        if self.admin:
            return Q()
        result = Q(pk__in=[])
        for kind in SCOPE_MODELS:
            ids = [scope.pk for scope in self.readable.values() if scope._meta.model_name == kind]
            result |= Q(**{f"{kind}_id__in": ids})
        return result


def add_resource(scope, uploaded, actor, title="", description=""):
    extension = Path(uploaded.name).suffix.lower()
    kind = (ScopeResource.IMAGE if extension in ScopeResource.IMAGE_EXTENSIONS else
            ScopeResource.VIDEO if extension in ScopeResource.VIDEO_EXTENSIONS else ScopeResource.FILE)
    resource = ScopeResource.objects.create(
        **{scope._meta.model_name: scope}, title=title or Path(uploaded.name).stem[:200],
        description=description, resource_type=kind, original_name=Path(uploaded.name).name[:255],
        file=uploaded, uploaded_by=actor,
    )
    log_change(actor, ChangeHistory.Action.UPLOAD, "Resource", resource.title,
               f"Uploaded {resource.get_resource_type_display().lower()} '{resource.title}' to {scope_label(scope)}.",
               entity_id=resource.pk, cohort=scope if isinstance(scope, Cohort) else None,
               details={"scope_ids": scope_ids(scope), "resource_model": "scope_resource",
                        "resource_type": kind, "filename": resource.original_name, "uploaded_by": actor.pk})
    return resource

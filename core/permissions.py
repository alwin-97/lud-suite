"""The single access rule for views: function views use @admin_required,
class-based views use AdminRequiredMixin / RoleRequiredMixin / RoleAccessRequiredMixin."""
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


DEFAULT_ROLE_PERMISSIONS = {
    "community_leader": {
        "cohorts": {"create": False, "read": True, "update": True, "delete": False},
        "terms": {"create": True, "read": True, "update": True, "delete": True},
        "resources": {"create": True, "read": True, "update": True, "delete": True},
        "activities": {"create": True, "read": True, "update": True, "delete": True},
        "tasks": {"create": True, "read": True, "update": True, "delete": True},
        "questions": {"create": True, "read": True, "update": True, "delete": True},
        "members": {"create": True, "read": True, "update": True, "delete": False},
        "audit_log": {"create": False, "read": True, "update": False, "delete": False},
        "reports": {"create": True, "read": True, "update": True, "delete": True},
    },
    "senior_member": {
        "cohorts": {"create": False, "read": True, "update": False, "delete": False},
        "terms": {"create": False, "read": True, "update": False, "delete": False},
        "resources": {"create": True, "read": True, "update": True, "delete": False},
        "activities": {"create": True, "read": True, "update": True, "delete": False},
        "tasks": {"create": True, "read": True, "update": True, "delete": False},
        "questions": {"create": True, "read": True, "update": True, "delete": False},
        "members": {"create": False, "read": True, "update": False, "delete": False},
        "audit_log": {"create": False, "read": True, "update": False, "delete": False},
        "reports": {"create": True, "read": True, "update": True, "delete": False},
    },
    "mentor": {
        "cohorts": {"create": False, "read": True, "update": False, "delete": False},
        "terms": {"create": False, "read": True, "update": False, "delete": False},
        "resources": {"create": False, "read": True, "update": False, "delete": False},
        "activities": {"create": False, "read": True, "update": True, "delete": False},
        "tasks": {"create": True, "read": True, "update": True, "delete": False},
        "questions": {"create": True, "read": True, "update": True, "delete": False},
        "members": {"create": False, "read": True, "update": False, "delete": False},
        "audit_log": {"create": False, "read": False, "update": False, "delete": False},
        "reports": {"create": True, "read": True, "update": True, "delete": False},
    },
    "mentee": {
        "cohorts": {"create": False, "read": True, "update": False, "delete": False},
        "terms": {"create": False, "read": True, "update": False, "delete": False},
        "resources": {"create": False, "read": True, "update": False, "delete": False},
        "activities": {"create": False, "read": True, "update": False, "delete": False},
        "tasks": {"create": False, "read": True, "update": False, "delete": False},
        "questions": {"create": False, "read": True, "update": False, "delete": False},
        "members": {"create": False, "read": True, "update": False, "delete": False},
        "audit_log": {"create": False, "read": False, "update": False, "delete": False},
        "reports": {"create": True, "read": True, "update": True, "delete": False},
    },
}


def has_role_permission(user, resource, action, cohort=None):
    """Check if the user has permission to perform `action` ('create', 'read', 'update', 'delete')
    on `resource` ('terms', 'resources', 'activities', 'members', 'cohorts', 'audit_log')."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_platform_admin", False):
        return True

    if cohort:
        roles = list(
            user.cohort_memberships.filter(cohort=cohort, is_active=True).values_list("role", flat=True)
        )
    else:
        roles = user.active_role_codes if not callable(user.active_role_codes) else user.active_role_codes()

    if not roles:
        return False

    from core.models import RolePermission

    pure_action = action.replace("can_", "")
    field_name = f"can_{pure_action}"

    db_perms = {
        (perm.role, perm.resource): getattr(perm, field_name, False)
        for perm in RolePermission.objects.filter(role__in=roles, resource=resource)
    }

    for role in roles:
        if (role, resource) in db_perms:
            if db_perms[(role, resource)]:
                return True
        else:
            default = DEFAULT_ROLE_PERMISSIONS.get(role, {}).get(resource, {}).get(pure_action, False)
            if default:
                return True

    return False


def get_mentor_assigned_mentee_ids(mentor_user, cohort=None):
    """Return set of mentee user IDs assigned to `mentor_user` (in `cohort` if specified)."""
    if not mentor_user or not getattr(mentor_user, "is_authenticated", False):
        return set()
    from core.models import CohortMembership, MentorAssignment

    q = {"mentor": mentor_user, "is_active": True}
    if cohort:
        target_cohort_id = cohort.pk if hasattr(cohort, "pk") else cohort
        q["cohort_id"] = target_cohort_id

    assigned_ids = set(
        MentorAssignment.objects.filter(**q).values_list("mentee_id", flat=True)
    )
    if assigned_ids:
        return assigned_ids

    # Fallback: if in this cohort no MentorAssignment has been configured yet,
    # return active mentees in the cohort(s) where mentor_user is a mentor.
    cohort_q = {"role": CohortMembership.MENTOR, "is_active": True, "user": mentor_user}
    if cohort:
        cohort_q["cohort_id"] = target_cohort_id
    mentor_cohort_ids = list(
        CohortMembership.objects.filter(**cohort_q).values_list("cohort_id", flat=True)
    )
    if not mentor_cohort_ids:
        return set()

    # If any MentorAssignment exists in these cohorts for any mentor, then this mentor simply has 0 assigned mentees
    if MentorAssignment.objects.filter(cohort_id__in=mentor_cohort_ids, is_active=True).exists():
        return set()

    # Otherwise fallback to cohort mentees
    return set(
        CohortMembership.objects.filter(
            cohort_id__in=mentor_cohort_ids,
            role=CohortMembership.MENTEE,
            is_active=True,
        ).values_list("user_id", flat=True)
    )


def get_senior_mentor_scoped_user_ids(senior_user, cohort=None):
    """Return set of all mentee and mentor user IDs in the scope of `senior_user`."""
    if not senior_user or not getattr(senior_user, "is_authenticated", False):
        return set()
    from core.models import CohortMembership

    q = {"user": senior_user, "is_active": True, "role": CohortMembership.SENIOR_MEMBER}
    if cohort:
        target_cohort_id = cohort.pk if hasattr(cohort, "pk") else cohort
        q["cohort_id"] = target_cohort_id

    senior_cohort_ids = list(
        CohortMembership.objects.filter(**q).values_list("cohort_id", flat=True)
    )
    if not senior_cohort_ids:
        return set()

    return set(
        CohortMembership.objects.filter(
            cohort_id__in=senior_cohort_ids,
            role__in=[CohortMembership.MENTEE, CohortMembership.MENTOR],
            is_active=True,
        ).values_list("user_id", flat=True)
    )


def can_user_view_member_data(viewer_user, target_user, cohort=None):
    """Determine if viewer_user can view target_user's submissions, reports, and data.
    - User can always view their own data.
    - Platform admin: can view all.
    - Community leader: can view all members in cohort.
    - Senior mentor (senior_member): can view all mentees and mentors in cohort.
    - Mentor: can view their assigned mentees in cohort.
    """
    if not viewer_user or not getattr(viewer_user, "is_authenticated", False):
        return False
    if getattr(viewer_user, "is_platform_admin", False):
        return True
    if viewer_user.pk == target_user.pk:
        return True

    from core.models import CohortMembership

    shared_memberships = viewer_user.cohort_memberships.filter(
        is_active=True,
        cohort__memberships__user=target_user,
        cohort__memberships__is_active=True,
    )
    if cohort:
        target_cohort_id = cohort.pk if hasattr(cohort, "pk") else cohort
        shared_memberships = shared_memberships.filter(cohort_id=target_cohort_id)

    if not shared_memberships.exists():
        return False

    for vm in shared_memberships:
        cid = vm.cohort_id
        # Community leader can view all cohort members
        if vm.role == CohortMembership.COMMUNITY_LEADER:
            return True

        # Senior Mentor can view all mentees and mentors in cohort scope
        if vm.role == CohortMembership.SENIOR_MEMBER:
            target_is_mentee_or_mentor = CohortMembership.objects.filter(
                cohort_id=cid,
                user=target_user,
                is_active=True,
                role__in=[CohortMembership.MENTEE, CohortMembership.MENTOR],
            ).exists()
            if target_is_mentee_or_mentor:
                return True

        # Mentor can view only their assigned mentees
        if vm.role == CohortMembership.MENTOR:
            mentee_ids = get_mentor_assigned_mentee_ids(viewer_user, cohort=cid)
            if target_user.pk in mentee_ids:
                return True

    return False


def can_manage_user_activity_report(user, target_user, action="read", cohort=None):
    """Check if `user` can perform `action` on activity reports for `target_user`."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    if user.pk == target_user.pk:
        # Users can view and prepare/edit their own reports
        if action in ("read", "create", "update"):
            return True
        return False

    # Check scoped access
    if not can_user_view_member_data(user, target_user, cohort=cohort):
        return False

    # Check shared active cohorts for action permissions
    shared_cohorts = list(
        user.cohort_memberships.filter(
            is_active=True,
            cohort__memberships__user=target_user,
            cohort__memberships__is_active=True,
        ).values_list("cohort_id", flat=True)
    )

    if cohort:
        target_cohort_id = cohort.pk if hasattr(cohort, "pk") else cohort
        shared_cohorts = [cid for cid in shared_cohorts if cid == target_cohort_id]

    if not shared_cohorts:
        return False

    for cid in shared_cohorts:
        if has_role_permission(user, "reports", action, cohort=cid):
            return True
    return False



def check_access(request, *, admin_only=False, required_roles=()):
    """Return a login redirect for anonymous users, raise PermissionDenied when
    the user lacks access, or return None when the request may proceed."""
    user = request.user
    if not user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if admin_only and not user.is_platform_admin:
        raise PermissionDenied
    if required_roles:
        role_codes = user.active_role_codes() if callable(user.active_role_codes) else user.active_role_codes
        if not set(required_roles) & set(role_codes):
            raise PermissionDenied
    return None


class RoleRequiredMixin:
    """Grant access when the user holds any of required_roles in an active cohort."""

    admin_only = False
    required_roles = ()

    def dispatch(self, request, *args, **kwargs):
        denied = check_access(
            request,
            admin_only=self.admin_only,
            required_roles=self.required_roles,
        )
        if denied is not None:
            return denied
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    admin_only = True


class RoleAccessRequiredMixin:
    """Enforce granular role-based access for CRUD operations."""

    permission_resource = ""
    permission_action = "read"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        cohort = getattr(self, "cohort", None)
        if not cohort and "cohort_id" in kwargs:
            try:
                from core.models import Cohort
                cohort = Cohort.objects.filter(pk=kwargs["cohort_id"]).first()
            except Exception:
                pass
        if not cohort and hasattr(self, "get_object"):
            try:
                from core.models import Cohort
                obj = self.get_object()
                cohort = obj if isinstance(obj, Cohort) else getattr(obj, "cohort", None)
            except Exception:
                pass

        if not has_role_permission(
            request.user,
            self.permission_resource,
            self.permission_action,
            cohort=cohort,
        ):
            raise PermissionDenied(
                f"You do not have permission to {self.permission_action} {self.permission_resource}."
            )

        return super().dispatch(request, *args, **kwargs)


"""Membership changes retain the row and write an actor/timestamp audit trail."""
from core.models import ChangeHistory, Cohort, CohortMembership, ScopeMembership, log_change
from core.services.audit import scope_ids


def membership_scope(membership):
    return membership.cohort if isinstance(membership, CohortMembership) else membership.scope


def record_membership(membership, actor, action, before=None):
    scope = membership_scope(membership)
    log_change(
        actor=actor, action=action, entity_type="Member", entity_id=membership.pk,
        entity_name=f"{membership.user.email} · {membership.get_role_display()} · {scope.name}"[:255],
        cohort=scope if isinstance(scope, Cohort) else None,
        description=(f"{ChangeHistory.Action(action).label} {membership.user} ({membership.user.email}) as "
                     f"{membership.get_role_display()} in {scope._meta.verbose_name} {scope.name}."),
        details={"user_id": membership.user_id, "user": membership.user.email,
                 "scope_type": scope._meta.model_name, "scope_id": scope.pk,
                 "scope_name": scope.name, "role": membership.role,
                 "scope_ids": scope_ids(scope),
                 "before_active": before, "is_active": membership.is_active},
    )


def set_membership_active(membership, active, actor):
    if membership.is_active == active:
        return
    before = membership.is_active
    membership.is_active = active
    membership.save(update_fields=["is_active"])
    record_membership(membership, actor,
                      ChangeHistory.Action.ACTIVATE if active else ChangeHistory.Action.DEACTIVATE,
                      before)


def add_membership(scope, user, role, actor):
    model = CohortMembership if isinstance(scope, Cohort) else ScopeMembership
    membership, created = model.objects.get_or_create(
        user=user, role=role, **{scope._meta.model_name: scope}, defaults={"is_active": True},
    )
    if created:
        record_membership(membership, actor, ChangeHistory.Action.ALLOCATE)
    else:
        set_membership_active(membership, True, actor)
    return membership

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from core.models import Mentee, MentorMenteeAssignment, RatingDomain, VolunteerReportingAssignment
from core.roles import role_layout


User = get_user_model()


def role_layout_context(user):
    active_role = getattr(user, "role", "")
    layout = role_layout(active_role)
    assigned_roles = list(getattr(user, "roles", None) or [])
    if active_role and active_role not in assigned_roles:
        assigned_roles.append(active_role)
    switchable_role_pairs = [(role, label) for role, label in user.get_role_pairs()] if getattr(user, "is_authenticated", False) else []
    can_switch_roles = "admin" in assigned_roles and len(assigned_roles) > 1
    return {
        "base_template": layout["base_template"],
        "home_url_name": layout["home_url_name"],
        "can_switch_roles": can_switch_roles,
        "switchable_role_pairs": switchable_role_pairs if can_switch_roles else [],
    }


def user_notification_groups(user):
    groups = set(getattr(user, "roles", None) or [])
    if getattr(user, "role", None):
        groups.add(user.role)
    if getattr(user, "is_superuser", False):
        groups.add("admin")
    groups.add("all")
    return groups


def active_assignments_qs(mentor):
    today = timezone.now().date()
    return MentorMenteeAssignment.objects.filter(
        mentor=mentor,
        is_active=True,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))


def get_mentee_for_user(user):
    return Mentee.objects.filter(user=user).first()


def volunteer_reporting_assignment_for(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return (
        VolunteerReportingAssignment.objects.select_related("programme", "location", "endorser")
        .filter(volunteer=user)
        .first()
    )


def mentor_can_access_mentee(user, mentee):
    if user.is_superuser or getattr(user, "role", None) == "admin":
        return True
    return active_assignments_qs(user).filter(mentee=mentee).exists()


def domains_for_year(year):
    return (
        RatingDomain.objects.filter(year=year, is_active=True)
        .prefetch_related("indicators", "scale_definitions")
        .order_by("sort_order", "name")
    )

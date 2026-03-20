from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from core.models import Mentee, MentorMenteeAssignment, RatingDomain


User = get_user_model()


def active_assignments_qs(mentor):
    today = timezone.now().date()
    return MentorMenteeAssignment.objects.filter(
        mentor=mentor,
        is_active=True,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))


def get_mentee_for_user(user):
    return Mentee.objects.filter(user=user).first()


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

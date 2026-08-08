from django.contrib.auth.models import AbstractUser
from django.db import models


def three_year_end_date(start_date):
    """Return the calendar date three years after ``start_date``."""

    try:
        return start_date.replace(year=start_date.year + 3)
    except ValueError:
        # A cohort starting on leap day ends on February 28 three years later.
        return start_date.replace(year=start_date.year + 3, day=28)


class CustomUser(AbstractUser):
    """A person who can access the platform after being provisioned by an admin."""

    ADMIN = "admin"
    ROLE_CHOICES = (
        ("", "Platform user"),
        (ADMIN, "Administrator"),
    )

    # Non-admin roles are assigned per cohort through CohortMembership. This
    # field remains the explicit marker for platform administrators.
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        blank=True,
        default="",
    )

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_platform_admin(self):
        return self.is_active and (
            self.is_staff or self.is_superuser or self.role == self.ADMIN
        )

    @property
    def is_authorized_user(self):
        if not self.is_active:
            return False
        if self.is_platform_admin:
            return True
        return self.cohort_memberships.filter(
            is_active=True,
            cohort__is_active=True,
            cohort__chapter__is_active=True,
            cohort__chapter__location__is_active=True,
        ).exists()

    def active_role_codes(self):
        if self.is_platform_admin:
            return [self.ADMIN]
        return list(
            self.cohort_memberships.filter(
                is_active=True,
                cohort__is_active=True,
                cohort__chapter__is_active=True,
                cohort__chapter__location__is_active=True,
            )
            .values_list("role", flat=True)
            .distinct()
            .order_by("role")
        )

    def __str__(self):
        return self.get_full_name() or self.email or self.username


class Location(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Chapter(models.Model):
    name = models.CharField(max_length=150)
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="chapters",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("location", "name"),
                name="unique_chapter_name_per_location",
            )
        ]

    def __str__(self):
        return f"{self.name} — {self.location.name}"


class Cohort(models.Model):
    name = models.CharField(max_length=150)
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.PROTECT,
        related_name="cohorts",
    )
    start_date = models.DateField()
    end_date = models.DateField(editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-start_date", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("chapter", "name"),
                name="unique_cohort_name_per_chapter",
            )
        ]

    def save(self, *args, **kwargs):
        self.end_date = three_year_end_date(self.start_date)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} — {self.chapter.name}"


class CohortMembership(models.Model):
    COMMUNITY_LEADER = "community_leader"
    MENTOR = "mentor"
    MENTEE = "mentee"

    ROLE_CHOICES = (
        (COMMUNITY_LEADER, "Community Leader"),
        (MENTOR, "Mentor"),
        (MENTEE, "Mentee"),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="cohort_memberships",
    )
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("cohort__chapter__name", "cohort__name", "role")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "cohort", "role"),
                name="unique_user_cohort_role",
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.cohort} — {self.get_role_display()}"

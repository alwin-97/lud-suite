import calendar

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models


def add_months(start_date, months):
    """Return the calendar date ``months`` after ``start_date``, clamping the day."""

    index = start_date.year * 12 + start_date.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    last_day = calendar.monthrange(year, month)[1]
    return start_date.replace(year=year, month=month, day=min(start_date.day, last_day))


# Filter applied to CohortMembership: the membership and everything above it
# (cohort, chapter, location, program) must be active.
ACTIVE_COHORT_CHAIN_FILTER = {
    "is_active": True,
    "chapter__is_active": True,
    "chapter__location__is_active": True,
    "chapter__location__program__is_active": True,
}

ACTIVE_MEMBERSHIP_FILTER = {
    "is_active": True,
    "cohort__is_active": True,
    "cohort__chapter__is_active": True,
    "cohort__chapter__location__is_active": True,
    "cohort__chapter__location__program__is_active": True,
}


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
        return self.cohort_memberships.filter(**ACTIVE_MEMBERSHIP_FILTER).exists()

    def active_role_codes(self):
        if self.is_platform_admin:
            return [self.ADMIN]
        return list(
            self.cohort_memberships.filter(**ACTIVE_MEMBERSHIP_FILTER)
            .values_list("role", flat=True)
            .distinct()
            .order_by("role")
        )

    def __str__(self):
        return self.get_full_name() or self.email or self.username


class Program(models.Model):
    """A Let Us Dream programme (e.g. DREAMS).

    A program owns its own tree of locations, chapters and cohorts, and sets how
    long its cohorts run. Platform roles are global (CustomUser.role); cohort
    roles are local to one cohort, and therefore to one program.
    """

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    duration_months = models.PositiveSmallIntegerField(
        default=36,
        validators=[MinValueValidator(1)],
        help_text="How long each cohort runs, in months. The cohort end date is calculated from this.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        previous = None
        if self.pk:
            previous = (
                Program.objects.filter(pk=self.pk)
                .values_list("duration_months", flat=True)
                .first()
            )
        super().save(*args, **kwargs)
        # Cohorts still on the calculated end date follow the new duration;
        # cohorts with a manually chosen end date are left alone.
        if previous is not None and previous != self.duration_months:
            for cohort in Cohort.objects.filter(chapter__location__program=self):
                if cohort.end_date == add_months(cohort.start_date, previous):
                    Cohort.objects.filter(pk=cohort.pk).update(
                        end_date=add_months(cohort.start_date, self.duration_months)
                    )

    def __str__(self):
        return self.name


class Location(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name="locations",
    )
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("program", "name"),
                name="unique_location_name_per_program",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.program.name})"


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
        return f"{self.name} — {self.location}"


class Cohort(models.Model):
    name = models.CharField(max_length=150)
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.PROTECT,
        related_name="cohorts",
    )
    start_date = models.DateField()
    # Blank means "start_date plus the program's duration" (set in save()).
    end_date = models.DateField(blank=True)
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

    @property
    def program(self):
        return self.chapter.location.program

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = add_months(self.start_date, self.program.duration_months)
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

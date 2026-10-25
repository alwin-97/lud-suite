import calendar

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


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

    @property
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

    def get_mentors(self):
        return CustomUser.objects.filter(
            cohort_memberships__cohort=self,
            cohort_memberships__role=CohortMembership.MENTOR,
            cohort_memberships__is_active=True,
        ).distinct()

    def get_senior_members(self):
        return CustomUser.objects.filter(
            cohort_memberships__cohort=self,
            cohort_memberships__role=CohortMembership.SENIOR_MEMBER,
            cohort_memberships__is_active=True,
        ).distinct()

    def get_mentees(self):
        return CustomUser.objects.filter(
            cohort_memberships__cohort=self,
            cohort_memberships__role=CohortMembership.MENTEE,
            cohort_memberships__is_active=True,
        ).distinct()


class CohortMembership(models.Model):
    COMMUNITY_LEADER = "community_leader"
    SENIOR_MEMBER = "senior_member"
    MENTOR = "mentor"
    MENTEE = "mentee"

    ROLE_CHOICES = (
        (COMMUNITY_LEADER, "Community Leader"),
        (SENIOR_MEMBER, "Senior Mentor / Member"),
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


class MentorAssignment(models.Model):
    """Pairing of a mentor to a mentee within a cohort."""

    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name="mentor_assignments",
    )
    mentor = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="mentee_assignments",
        help_text="The mentor assigned.",
    )
    mentee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="mentor_assignments",
        help_text="The mentee assigned.",
    )
    assigned_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_mentor_assignments",
    )
    notes = models.TextField(blank=True, help_text="Notes or goals for this mentorship pairing.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("cohort__name", "mentor__first_name", "mentee__first_name")
        constraints = [
            models.UniqueConstraint(
                fields=("cohort", "mentor", "mentee"),
                name="unique_cohort_mentor_mentee_assignment",
            )
        ]

    def __str__(self):
        return f"{self.mentor} -> {self.mentee} ({self.cohort.name})"


class Term(models.Model):
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name="terms",
    )
    name = models.CharField(max_length=150)
    sequence = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Sequence order of this term within the cohort (e.g. 1 for Term 1).",
    )
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sequence", "start_date", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("cohort", "name"),
                name="unique_term_name_per_cohort",
            )
        ]

    def __str__(self):
        return f"{self.name} — {self.cohort.name}"


class TermResource(models.Model):
    DOCUMENT = "document"
    IMAGE = "image"
    LINK = "link"

    RESOURCE_TYPE_CHOICES = (
        (DOCUMENT, "Document"),
        (IMAGE, "Image"),
        (LINK, "Link / URL"),
    )

    IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "svg"}

    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        related_name="resources",
    )
    title = models.CharField(max_length=200, help_text="Display title for this resource.")
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)
    file = models.FileField(upload_to="terms/resources/", blank=True, null=True)
    url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Web address / external link (e.g. https://...)",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.title} ({self.get_resource_type_display()})"

    @property
    def file_extension(self):
        if self.file and "." in self.file.name:
            return self.file.name.rsplit(".", 1)[-1].lower()
        return ""

    @property
    def is_image(self):
        if self.resource_type == self.IMAGE:
            return True
        return self.file_extension in self.IMAGE_EXTENSIONS

    @property
    def is_document(self):
        return self.resource_type == self.DOCUMENT

    @property
    def is_link(self):
        return self.resource_type == self.LINK


class ChangeHistory(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Created"
        UPDATE = "update", "Updated"
        DELETE = "delete", "Deleted"
        ALLOCATE = "allocate", "Allocated"
        REALLOCATE = "reallocate", "Reallocated"
        ACTIVATE = "activate", "Activated"
        DEACTIVATE = "deactivate", "Deactivated"
        UPLOAD = "upload", "Uploaded"
        REMOVE = "remove", "Removed"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performed_changes",
        help_text="The user who performed the change.",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    entity_type = models.CharField(
        max_length=50,
        help_text="e.g. Program, Location, Chapter, Cohort, Term, Resource, Member, User",
    )
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    entity_name = models.CharField(max_length=255)
    description = models.TextField(help_text="Human-readable summary of the change.")
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="change_history",
        help_text="Associated cohort if applicable.",
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured details or field-level differences.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "Change histories"

    def __str__(self):
        actor_name = self.actor.get_full_name() or self.actor.email if self.actor else "System"
        return f"{self.created_at:%d %b %Y %H:%M} · {actor_name} {self.get_action_display().lower()} {self.entity_type}: {self.entity_name}"

    @property
    def action_icon(self):
        icons = {
            self.Action.CREATE: "fi-rr-plus",
            self.Action.UPDATE: "fi-rr-pencil",
            self.Action.DELETE: "fi-rr-trash",
            self.Action.ALLOCATE: "fi-rr-user-add",
            self.Action.REALLOCATE: "fi-rr-user-arrows-swap",
            self.Action.ACTIVATE: "fi-rr-play",
            self.Action.DEACTIVATE: "fi-rr-pause",
            self.Action.UPLOAD: "fi-rr-upload",
            self.Action.REMOVE: "fi-rr-cross",
        }
        return icons.get(self.action, "fi-rr-info")

    @property
    def action_badge_class(self):
        classes = {
            self.Action.CREATE: "status-badge status-badge--active",
            self.Action.UPDATE: "status-badge",
            self.Action.DELETE: "status-badge status-badge--danger",
            self.Action.ALLOCATE: "status-badge status-badge--active",
            self.Action.REALLOCATE: "status-badge status-badge--warning",
            self.Action.ACTIVATE: "status-badge status-badge--active",
            self.Action.DEACTIVATE: "status-badge status-badge--warning",
            self.Action.UPLOAD: "status-badge status-badge--active",
            self.Action.REMOVE: "status-badge status-badge--danger",
        }
        return classes.get(self.action, "status-badge")

    @property
    def actor_name(self):
        if self.actor:
            return self.actor.get_full_name() or self.actor.email
        return "System"


class CohortActivity(models.Model):
    """Activity or milestone on a cohort's timeline planned within a term."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        DELAYED = "delayed", "Delayed"

    class TargetAudience(models.TextChoices):
        ALL = "all", "All Cohort Members"
        SENIOR_MEMBERS = "senior_members", "Senior Members"
        MENTORS = "mentors", "Mentors"
        MENTEES = "mentees", "Mentees"
        COMMUNITY_LEADERS = "community_leaders", "Community Leaders"

    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        related_name="activities",
        help_text="The term this activity is scheduled in.",
    )
    title = models.CharField(max_length=200, help_text="Activity or milestone title.")
    description = models.TextField(blank=True, help_text="Objectives, deliverables, or agenda.")
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    target_audience = models.CharField(
        max_length=30,
        choices=TargetAudience.choices,
        default=TargetAudience.ALL,
        help_text="Member format/category participating in this activity.",
    )
    sequence = models.PositiveSmallIntegerField(
        default=1,
        help_text="Sequence order within the term.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("term__sequence", "sequence", "start_date", "title")
        verbose_name_plural = "Cohort activities"

    def __str__(self):
        return f"{self.term.name}: {self.title} ({self.get_status_display()})"

    @property
    def status_badge_class(self):
        badges = {
            self.Status.COMPLETED: "status-badge status-badge--active",
            self.Status.IN_PROGRESS: "status-badge status-badge--active",
            self.Status.PLANNED: "status-badge",
            self.Status.DELAYED: "status-badge status-badge--danger",
        }
        return badges.get(self.status, "status-badge")


class RolePermission(models.Model):
    """Configurable role-based access for CRUD operations across platform resources."""

    class Resource(models.TextChoices):
        TERMS = "terms", "Cohort Terms"
        RESOURCES = "resources", "Term Resources (Files & URLs)"
        ACTIVITIES = "activities", "Cohort Activities & Timeline"
        MEMBERS = "members", "Member Allocation & Reallocation"
        COHORTS = "cohorts", "Cohorts & Structure"
        AUDIT_LOG = "audit_log", "Audit Trail & Logs"
        REPORTS = "reports", "User Activity Reports"
        TASKS = "tasks", "Term Tasks & Submissions"
        QUESTIONS = "questions", "Term Questions & Responses"

    role = models.CharField(max_length=30, choices=CohortMembership.ROLE_CHOICES)
    resource = models.CharField(max_length=30, choices=Resource.choices)
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=True)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("role", "resource")
        constraints = [
            models.UniqueConstraint(
                fields=("role", "resource"),
                name="unique_role_resource_permission",
            )
        ]

    def __str__(self):
        perms = []
        if self.can_create:
            perms.append("Create")
        if self.can_read:
            perms.append("Read")
        if self.can_update:
            perms.append("Update")
        if self.can_delete:
            perms.append("Delete")
        return f"{self.get_role_display()} — {self.get_resource_display()}: {', '.join(perms) or 'None'}"


class UserActivityReport(models.Model):
    """Activity report prepared by or for a cohort participant tracking engagement,
    deliverables, milestones, reflections, and hours spent."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"
        APPROVED = "approved", "Approved"

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="activity_reports",
        help_text="The participant whose activities are being reported.",
    )
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name="activity_reports",
        help_text="The cohort in which these activities took place.",
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_activity_reports",
        help_text="Optional term context.",
    )
    activity = models.ForeignKey(
        CohortActivity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_reports",
        help_text="Specific planned cohort activity or milestone, if applicable.",
    )
    title = models.CharField(max_length=200, help_text="Report title or activity summary heading.")
    report_date = models.DateField(default=timezone.now, help_text="Date of reporting or activity completion.")
    hours_spent = models.DecimalField(
        max_digits=5, decimal_places=1, default=0.0, help_text="Hours invested in this activity/period."
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    progress_status = models.CharField(
        max_length=20,
        choices=CohortActivity.Status.choices,
        default=CohortActivity.Status.COMPLETED,
        help_text="Milestone or task progress outcome.",
    )
    summary = models.TextField(help_text="Summary of activities performed, deliverables completed, or achievements.")
    reflections = models.TextField(
        blank=True, help_text="Learnings, key takeaways, personal growth, and mentorship insights."
    )
    challenges = models.TextField(
        blank=True, help_text="Obstacles or roadblocks encountered and how they were resolved."
    )
    next_steps = models.TextField(
        blank=True, help_text="Planned goals, commitments, and action items for the upcoming term/period."
    )
    attachment = models.FileField(
        upload_to="activity_reports/%Y/%m/",
        blank=True,
        null=True,
        help_text="Supporting evidence, photos, presentations, work files, or documentation.",
    )
    feedback = models.TextField(
        blank=True, help_text="Reviewer or leader feedback and evaluation notes."
    )
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_activity_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-report_date", "-created_at")
        verbose_name = "User activity report"
        verbose_name_plural = "User activity reports"

    def __str__(self):
        return f"{self.user} — {self.title} ({self.get_status_display()})"

    @property
    def status_badge_class(self):
        badges = {
            self.Status.APPROVED: "status-badge status-badge--active",
            self.Status.REVIEWED: "status-badge status-badge--active",
            self.Status.SUBMITTED: "status-badge",
            self.Status.DRAFT: "status-badge status-badge--muted",
        }
        return badges.get(self.status, "status-badge")

    @property
    def file_extension(self):
        if not self.attachment or not self.attachment.name:
            return ""
        from pathlib import Path
        return Path(self.attachment.name).suffix.lower().lstrip(".")


class TermTask(models.Model):
    """A task/assignment created under a cohort term accepting file, text, url, or image submissions."""

    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        related_name="tasks",
        help_text="The cohort term this task belongs to.",
    )
    title = models.CharField(max_length=200, help_text="Task title or milestone name.")
    description = models.TextField(help_text="Detailed instructions, deliverables, requirements, or prompts.")
    target_audience = models.CharField(
        max_length=30,
        choices=CohortActivity.TargetAudience.choices,
        default=CohortActivity.TargetAudience.ALL,
        help_text="Target member format (e.g. All, Mentees, Mentors, Senior Members).",
    )
    due_date = models.DateField(blank=True, null=True, help_text="Optional submission deadline.")
    points = models.PositiveIntegerField(default=100, blank=True, null=True, help_text="Maximum points or score.")

    # Forms of submission accepted
    allow_text = models.BooleanField(default=True, help_text="Accept written text or reflections.")
    allow_file = models.BooleanField(default=True, help_text="Accept document file uploads (PDF, DOCX, etc.).")
    allow_url = models.BooleanField(default=True, help_text="Accept external links / URLs (Google Drive, GitHub, etc.).")
    allow_image = models.BooleanField(default=True, help_text="Accept image uploads (PNG, JPG, etc.).")

    sequence = models.PositiveSmallIntegerField(default=1, help_text="Order of display within the term.")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("term__sequence", "sequence", "due_date", "title")
        verbose_name = "Term task"
        verbose_name_plural = "Term tasks"

    def __str__(self):
        return f"{self.term.name}: {self.title}"

    @property
    def cohort(self):
        return self.term.cohort

    @property
    def allowed_types_display(self):
        types = []
        if self.allow_text:
            types.append("Text")
        if self.allow_file:
            types.append("File")
        if self.allow_url:
            types.append("URL")
        if self.allow_image:
            types.append("Image")
        return ", ".join(types) or "None"


class TaskSubmission(models.Model):
    """A participant's submission for a TermTask, containing text, file, url, or image."""

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"
        APPROVED = "approved", "Approved"
        NEEDS_REVISION = "needs_revision", "Needs Revision"

    task = models.ForeignKey(
        TermTask,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="task_submissions",
    )
    text_response = models.TextField(blank=True, help_text="Written text submission or notes.")
    file_submission = models.FileField(
        upload_to="task_submissions/files/%Y/%m/",
        blank=True,
        null=True,
        help_text="Document attachment (PDF, DOCX, ZIP, etc.).",
    )
    image_submission = models.FileField(
        upload_to="task_submissions/images/%Y/%m/",
        blank=True,
        null=True,
        help_text="Image submission (PNG, JPG, etc.).",
    )
    url_submission = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Link / URL to external work (Google Drive, GitHub repo, live site, etc.).",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Score or grade awarded (out of max points).",
    )
    feedback = models.TextField(blank=True, help_text="Reviewer / mentor feedback and remarks.")
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_task_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-submitted_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("task", "user"),
                name="unique_user_task_submission",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.task.title} ({self.get_status_display()})"

    @property
    def status_badge_class(self):
        badges = {
            self.Status.APPROVED: "status-badge status-badge--active",
            self.Status.REVIEWED: "status-badge status-badge--active",
            self.Status.SUBMITTED: "status-badge",
            self.Status.NEEDS_REVISION: "status-badge status-badge--danger",
        }
        return badges.get(self.status, "status-badge")

    @property
    def file_extension(self):
        if self.file_submission and "." in self.file_submission.name:
            return self.file_submission.name.rsplit(".", 1)[-1].lower()
        return ""

    @property
    def has_content(self):
        return bool(self.text_response or self.file_submission or self.image_submission or self.url_submission)


class TermQuestion(models.Model):
    """A question / inquiry / assessment prompt created under a cohort term."""

    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        related_name="questions",
        help_text="The cohort term this question belongs to.",
    )
    title = models.CharField(max_length=200, help_text="Question topic or short label.")
    prompt = models.TextField(help_text="The question prompt, inquiry, or challenge.")
    help_text = models.TextField(blank=True, help_text="Guidance, hints, context, or instructions.")
    target_audience = models.CharField(
        max_length=30,
        choices=CohortActivity.TargetAudience.choices,
        default=CohortActivity.TargetAudience.ALL,
        help_text="Target participant category.",
    )
    due_date = models.DateField(blank=True, null=True, help_text="Optional response deadline.")
    is_required = models.BooleanField(default=True, help_text="Whether this question is mandatory.")

    # Forms of submission accepted
    allow_text = models.BooleanField(default=True, help_text="Accept text responses.")
    allow_file = models.BooleanField(default=True, help_text="Accept file uploads.")
    allow_url = models.BooleanField(default=True, help_text="Accept external links / URLs.")
    allow_image = models.BooleanField(default=True, help_text="Accept image uploads.")

    sequence = models.PositiveSmallIntegerField(default=1, help_text="Order within term.")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_questions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("term__sequence", "sequence", "due_date", "title")
        verbose_name = "Term question"
        verbose_name_plural = "Term questions"

    def __str__(self):
        return f"{self.term.name}: {self.title}"

    @property
    def cohort(self):
        return self.term.cohort

    @property
    def allowed_types_display(self):
        types = []
        if self.allow_text:
            types.append("Text")
        if self.allow_file:
            types.append("File")
        if self.allow_url:
            types.append("URL")
        if self.allow_image:
            types.append("Image")
        return ", ".join(types) or "None"


class QuestionResponse(models.Model):
    """A participant's answer to a TermQuestion, supporting text, file, url, or image."""

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"
        APPROVED = "approved", "Approved"

    question = models.ForeignKey(
        TermQuestion,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="question_responses",
    )
    text_response = models.TextField(blank=True, help_text="Written answer / response.")
    file_submission = models.FileField(
        upload_to="question_responses/files/%Y/%m/",
        blank=True,
        null=True,
        help_text="File attachment.",
    )
    image_submission = models.FileField(
        upload_to="question_responses/images/%Y/%m/",
        blank=True,
        null=True,
        help_text="Image submission.",
    )
    url_submission = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Web address / URL.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    feedback = models.TextField(blank=True, help_text="Mentor or reviewer feedback.")
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_question_responses",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-submitted_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("question", "user"),
                name="unique_user_question_response",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.question.title} ({self.get_status_display()})"

    @property
    def status_badge_class(self):
        badges = {
            self.Status.APPROVED: "status-badge status-badge--active",
            self.Status.REVIEWED: "status-badge status-badge--active",
            self.Status.SUBMITTED: "status-badge",
        }
        return badges.get(self.status, "status-badge")

    @property
    def file_extension(self):
        if self.file_submission and "." in self.file_submission.name:
            return self.file_submission.name.rsplit(".", 1)[-1].lower()
        return ""

    @property
    def has_content(self):
        return bool(self.text_response or self.file_submission or self.image_submission or self.url_submission)




def log_change(
    actor,
    action,
    entity_type,
    entity_name,
    description,
    *,
    entity_id=None,
    cohort=None,
    details=None,
):
    """Record a change in ChangeHistory."""
    user = actor if (actor and getattr(actor, "is_authenticated", False)) else None
    return ChangeHistory.objects.create(
        actor=user,
        action=action,
        entity_type=entity_type,
        entity_name=str(entity_name),
        entity_id=entity_id,
        description=description,
        cohort=cohort,
        details=details or {},
    )



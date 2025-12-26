from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator



# -------------------- Custom User --------------------
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('endorser', 'Endorser'),
        ('mentor', 'Mentor'),
        ('mentee', 'Mentee'),
        ('reviewer', 'Reviewer'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    religion = models.CharField(max_length=50, blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    institution = models.CharField(max_length=150, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)

    # ManyToMany for mentors assigned to endorsers
    mentors = models.ManyToManyField(
        'self', blank=True, symmetrical=False, related_name='assigned_endorsers'
    )

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def mentee_profile_safe(self):
        try:
            return self.mentee_profile
        except Mentee.DoesNotExist:
            return None


# -------------------- Activity Model --------------------
class Activity(models.Model):
    ACTIVITY_CHOICES = [
        ('YCLP-Class', 'YCLP-Class'),
        ('DREAMS Summer Camp', 'DREAMS Summer Camp'),
        ('DREAMS Follow-Up', 'DREAMS Follow-Up'),
        ('Others', 'Others'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    duration = models.DecimalField(max_digits=4, decimal_places=2)
    activity = models.CharField(max_length=255, choices=ACTIVITY_CHOICES, default='YCLP-Class')
    other_activity = models.CharField(max_length=255, blank=True, null=True)
    learnings = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    remark = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity} on {self.date}"


# -------------------- Assignment Model --------------------
class Assignment(models.Model):
    endorser = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignments'
    )
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentorships'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.endorser} → {self.mentor}"


# -------------------- Notification --------------------
class Notification(models.Model):
    ROLE_CHOICES = [
        ('endorser', 'Endorser'),
        ('mentor', 'Mentor'),
        ('both', 'Both'),
    ]
    message = models.TextField()
    target_group = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )

    def __str__(self):
        return f"{self.target_group} - {self.message[:30]}"


# -------------------- Mentor Profile / WorkSchedule --------------------
class MentorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentor_profile",
        limit_choices_to={"role": "mentor"},
    )
    name = models.CharField(max_length=100)
    email = models.EmailField()
    register_no = models.CharField(max_length=50)
    cls = models.CharField(max_length=50)
    department = models.CharField(max_length=100, blank=True)
    affiliation = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.name




class WorkSchedule(models.Model):
    endorser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='schedules')
    mentors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='mentor_schedules')
    role = models.CharField(max_length=100)
    due_date = models.DateField()
    description = models.TextField()

    def __str__(self):
        return f"{self.endorser.username} - {self.role} due {self.due_date}"


# -------------------- DIP Mentee Tracker --------------------
class ProgramYear(models.IntegerChoices):
    YEAR_1 = 1, "Year 1"
    YEAR_2 = 2, "Year 2"
    YEAR_3 = 3, "Year 3"
    YEAR_4 = 4, "Year 4"


class School(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Mentee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentee_profile",
        limit_choices_to={"role": "mentee"},
    )
    full_name = models.CharField(max_length=150)
    grade = models.CharField(max_length=50, blank=True)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    programme = models.CharField(max_length=150, blank=True)
    department = models.CharField(max_length=150, blank=True)
    batch = models.CharField(max_length=100, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    expected_completion_date = models.DateField(null=True, blank=True)
    current_year = models.PositiveSmallIntegerField(choices=ProgramYear.choices)
    assigned_mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_mentees",
        limit_choices_to={"role": "mentor"},
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        if self.user:
            return f"{self.user.get_full_name()} ({self.user.username})"
        return self.full_name


class MenteeProfile(Mentee):
    class Meta:
        proxy = True
        verbose_name = "Mentee Profile"
        verbose_name_plural = "Mentee Profiles"


class MentorMenteeAssignment(models.Model):
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mentee_assignments",
        limit_choices_to={"role": "mentor"},
    )
    mentee = models.ForeignKey(
        Mentee,
        on_delete=models.CASCADE,
        related_name="mentor_assignments",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        unique_together = [("mentor", "mentee", "start_date")]

    def __str__(self):
        return f"{self.mentor} → {self.mentee}"


class StatusConfig(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=30, blank=True)
    ordering = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordering", "name"]

    def __str__(self):
        return self.name


class TemplateConfig(models.Model):
    class Scope(models.TextChoices):
        OBJECTIVE = "objective", "Objective"
        YEAR_PLAN = "year_plan", "Year Plan"

    name = models.CharField(max_length=120)
    scope = models.CharField(max_length=20, choices=Scope.choices)
    year = models.PositiveSmallIntegerField(choices=ProgramYear.choices, null=True, blank=True)
    fields_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["scope", "year", "name"]
        unique_together = [("scope", "year", "name")]

    def __str__(self):
        if self.year:
            return f"{self.name} ({self.get_year_display()})"
        return self.name


class ObjectiveItem(models.Model):
    mentee = models.ForeignKey(Mentee, on_delete=models.CASCADE, related_name="objective_items")
    objective_title = models.CharField(max_length=200, blank=True)
    objective_text = models.TextField(blank=True)
    action_items = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    expected_outcome = models.TextField(blank=True)
    status = models.ForeignKey(StatusConfig, on_delete=models.PROTECT, null=True, blank=True)
    progress_percent = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True,
    )
    evidence = models.FileField(upload_to="evidence/", blank=True, null=True)
    mentee_remarks = models.TextField(blank=True)
    mentor_comments = models.TextField(blank=True)
    mentor_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="objective_items_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="objective_items_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "objective_title"]

    def __str__(self):
        return f"{self.mentee} - {self.objective_title or 'Objective'}"


class YearPlanItem(models.Model):
    mentee = models.ForeignKey(Mentee, on_delete=models.CASCADE, related_name="year_plan_items")
    year = models.PositiveSmallIntegerField(choices=ProgramYear.choices)
    milestone = models.CharField(max_length=200)
    deliverable = models.TextField(blank=True)
    target_date = models.DateField(null=True, blank=True)
    target_period = models.CharField(max_length=100, blank=True)
    status = models.ForeignKey(StatusConfig, on_delete=models.PROTECT, null=True, blank=True)
    remarks = models.TextField(blank=True)
    mentor_comments = models.TextField(blank=True)
    review_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="year_plan_items_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="year_plan_items_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["year", "-updated_at"]

    def __str__(self):
        return f"{self.mentee} - {self.get_year_display()} - {self.milestone}"


class DomainIndicator(models.Model):
    domain = models.ForeignKey("RatingDomain", on_delete=models.CASCADE, related_name="indicators")
    description = models.TextField()
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["domain__year", "domain__sort_order", "sort_order"]
        unique_together = [("domain", "sort_order")]

    def __str__(self):
        return f"{self.domain} - {self.sort_order}"


class RatingScaleDefinition(models.Model):
    domain = models.ForeignKey("RatingDomain", on_delete=models.CASCADE, related_name="scale_definitions")
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    description = models.TextField()

    class Meta:
        ordering = ["domain__year", "domain__sort_order", "score"]
        unique_together = [("domain", "score")]

    def __str__(self):
        return f"{self.domain} - {self.score}"


class MoodCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    mood_types = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class ReferenceContent(models.Model):
    section = models.CharField(max_length=100)
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["section", "sort_order"]

    def __str__(self):
        return f"{self.section}: {self.title or 'Entry'}"


class SessionType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RatingDomain(models.Model):
    class Source(models.TextChoices):
        OBJECTIVE = "objective", "Objective"
        TRACKER = "tracker", "Tracker"

    year = models.PositiveSmallIntegerField(choices=ProgramYear.choices)
    name = models.CharField(max_length=150)
    source = models.CharField(max_length=20, choices=Source.choices)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["year", "sort_order", "name"]
        unique_together = [("year", "name")]

    def __str__(self):
        return f"{self.get_year_display()} - {self.name}"


class MenteeAssessment(models.Model):
    mentee = models.ForeignKey(Mentee, on_delete=models.CASCADE, related_name="assessments")
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="mentee_assessments",
        limit_choices_to={"role": "mentor"},
    )
    year = models.PositiveSmallIntegerField(choices=ProgramYear.choices)
    session_type = models.ForeignKey(SessionType, on_delete=models.PROTECT)
    date = models.DateField()
    theme_topic = models.CharField(max_length=200, blank=True)
    beginning_mood = models.CharField(max_length=100, blank=True)
    end_mood = models.CharField(max_length=100, blank=True)
    mentor_remarks = models.TextField(blank=True)
    action_plan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "mentee__full_name"]

    def __str__(self):
        return f"{self.mentee} - {self.get_year_display()} - {self.date}"

    def average_score(self):
        scores = list(self.ratings.values_list("value", flat=True))
        if not scores:
            return None
        return round(sum(scores) / len(scores), 2)


class AssessmentRating(models.Model):
    assessment = models.ForeignKey(MenteeAssessment, on_delete=models.CASCADE, related_name="ratings")
    domain = models.ForeignKey(RatingDomain, on_delete=models.PROTECT)
    value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        unique_together = [("assessment", "domain")]
        ordering = ["domain__year", "domain__sort_order", "domain__name"]

    def __str__(self):
        return f"{self.assessment} - {self.domain.name}: {self.value}"


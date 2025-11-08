from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# -------------------- Custom User --------------------
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('endorser', 'Endorser'),
        ('mentor', 'Mentor'),
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
    name = models.CharField(max_length=100)
    email = models.EmailField()
    register_no = models.CharField(max_length=50)
    cls = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class WorkSchedule(models.Model):
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE)
    role = models.CharField(max_length=50)
    due_date = models.DateField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mentor.name} - {self.role} due {self.due_date}"

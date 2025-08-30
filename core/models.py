from django.db import models
from django.contrib.auth.models import User

class Activity(models.Model):
    ACTIVITY_CHOICES = [
        ('YCLP-Class', 'YCLP-Class'),
        ('DREAMS Summer Camp', 'DREAMS Summer Camp'),
        ('DREAMS Follow-Up', 'DREAMS Follow-Up'),
        ('Others', 'Others'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    duration = models.DecimalField(max_digits=4, decimal_places=2)
    activity = models.CharField(max_length=255, choices=ACTIVITY_CHOICES, default='YCLP-Class')
    other_activity = models.CharField(max_length=255, blank=True, null=True)
    learnings = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity} on {self.date}"
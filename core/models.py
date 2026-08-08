from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """The authenticated administrator for the application."""

    ADMIN = "admin"
    ROLE_CHOICES = ((ADMIN, "Admin"),)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ADMIN,
    )

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_platform_admin(self):
        return self.is_active and (self.is_superuser or self.role == self.ADMIN)

    def __str__(self):
        return self.email or self.username

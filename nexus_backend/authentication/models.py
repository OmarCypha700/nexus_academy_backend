from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ("student", "Student"),
        ("instructor", "Instructor"),
        ("admin", "Admin"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    position = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    is_instructor = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"


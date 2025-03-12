from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    department = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

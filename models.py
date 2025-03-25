from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    department = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
class HealthCheckCard(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(HealthCheckCard, on_delete=models.CASCADE)
    value = models.CharField(max_length=10, choices=[
        ('green', 'Green'),
        ('amber', 'Amber'),
        ('red', 'Red')
    ])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

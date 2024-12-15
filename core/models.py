from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    team = models.ForeignKey('Team', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class Team(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    
    def __str__(self):
        return f'{self.name} ({self.department.name})'

class Session(models.Model):
    name = models.CharField(max_length=100, default='Health Check Session')
    date = models.DateField()
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f'{self.name} - {self.date}'
    
    class Meta:
        ordering = ['-date']

class HealthCheckCard(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Vote(models.Model):
    VOTE_CHOICES = (
        ('green', 'Green - Good'),
        ('amber', 'Amber - Concerning'),
        ('red', 'Red - Bad'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(HealthCheckCard, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    value = models.CharField(max_length=5, choices=VOTE_CHOICES)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'card', 'session')
    
    def __str__(self):
        return f'{self.user.username} - {self.card.name} - {self.value}'

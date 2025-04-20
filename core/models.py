
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class User(AbstractUser):
    ROLES = (
        ('engineer', 'Engineer'),
        ('team_leader', 'Team Leader'),
        ('department_leader', 'Department Leader'),
        ('senior_manager', 'Senior Manager'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLES)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    team = models.ForeignKey('Team', on_delete=models.SET_NULL, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    bio = models.TextField(blank=True, null=True)

    # Add related_name to avoid conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def get_recent_votes(self):
        """Return user's votes from the most recent session"""
        recent_session = Session.objects.filter(is_active=True).order_by('-date').first()
        if recent_session:
            return Vote.objects.filter(user=self, session=recent_session)
        return Vote.objects.none()
    
    def has_voted_in_session(self, session):
        """Check if user has voted in a specific session"""
        return Vote.objects.filter(user=self, session=session).exists()
    
    def can_manage_team(self, team):
        """Check if user has permission to manage the given team"""
        if self.role == 'admin' or self.role == 'senior_manager':
            return True
        if self.role == 'department_leader' and team.department == self.department:
            return True
        if self.role == 'team_leader' and team == self.team:
            return True
        return False
    
    def can_view_department_summary(self, department):
        """Check if user has permission to view department summary"""
        if self.role == 'admin' or self.role == 'senior_manager':
            return True
        if self.role == 'department_leader' and department == self.department:
            return True
        return False

class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name
    
    def get_team_count(self):
        return self.team_set.count()
    
    def get_member_count(self):
        """Return the number of users in this department"""
        return User.objects.filter(department=self).count()
    
    def get_teams(self):
        """Return all teams in this department"""
        return self.team_set.all()
    
    def get_active_teams(self):
        """Return teams with at least one member"""
        return self.team_set.filter(user__isnull=False).distinct()

class Team(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.name} ({self.department.name})"
    
    def get_member_count(self):
        return User.objects.filter(team=self).count()
    
    def get_members(self):
        """Return all users in this team"""
        return User.objects.filter(team=self)
    
    def get_team_leaders(self):
        """Return all team leaders for this team"""
        return User.objects.filter(team=self, role='team_leader')
    
    def get_latest_health_status(self):
        """Return the latest overall health status of the team"""
        latest_session = Session.objects.filter(is_active=True).order_by('-date').first()
        if not latest_session:
            return None
        
        team_summaries = TeamSummary.objects.filter(team=self, session=latest_session)
        if not team_summaries.exists():
            return None
        
        # Count votes by color
        red_count = team_summaries.filter(average_vote='red').count()
        amber_count = team_summaries.filter(average_vote='amber').count()
        green_count = team_summaries.filter(average_vote='green').count()
        
        # Determine overall status
        if red_count > amber_count and red_count > green_count:
            return 'red'
        elif amber_count > red_count and amber_count > green_count:
            return 'amber'
        elif green_count > 0:
            return 'green'
        return None

class Session(models.Model):
    name = models.CharField(max_length=100, default="Health Check Session")
    date = models.DateField()
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.name} - {self.date}"
    
    class Meta:
        ordering = ['-date']
    
    def get_participation_rate(self, team=None):
        """Return the participation rate for this session, optionally filtered by team"""
        if team:
            eligible_users = User.objects.filter(team=team).count()
            if eligible_users == 0:
                return 0
            participants = Vote.objects.filter(session=self, user__team=team).values('user').distinct().count()
            return (participants / eligible_users) * 100
        else:
            eligible_users = User.objects.all().count()
            if eligible_users == 0:
                return 0
            participants = Vote.objects.filter(session=self).values('user').distinct().count()
            return (participants / eligible_users) * 100
    
    def is_complete(self):
        """Check if all eligible users have voted in this session"""
        eligible_users = User.objects.filter(role__in=['engineer', 'team_leader']).count()
        participants = Vote.objects.filter(session=self).values('user').distinct().count()
        return eligible_users == participants

class HealthCheckCard(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['order']
    
    def get_vote_distribution(self, session=None):
        """Return the distribution of votes for this card, optionally filtered by session"""
        votes = Vote.objects.filter(card=self)
        if session:
            votes = votes.filter(session=session)
        
        total = votes.count()
        if total == 0:
            return {'green': 0, 'amber': 0, 'red': 0}
        
        green = votes.filter(value='green').count()
        amber = votes.filter(value='amber').count()
        red = votes.filter(value='red').count()
        
        return {
            'green': (green / total) * 100,
            'amber': (amber / total) * 100,
            'red': (red / total) * 100
        }

class Vote(models.Model):
    VOTE_CHOICES = (
        ('green', 'Green'),
        ('amber', 'Amber'),
        ('red', 'Red'),
    )
    PROGRESS_CHOICES = (
        ('better', 'Better'),
        ('same', 'Same'),
        ('worse', 'Worse'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(HealthCheckCard, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    value = models.CharField(max_length=5, choices=VOTE_CHOICES)
    progress_note = models.CharField(max_length=6, choices=PROGRESS_CHOICES)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'card', 'session')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.card.name} - {self.value}"
    
    def get_previous_vote(self):
        """Return the previous vote by the same user for the same card"""
        previous_sessions = Session.objects.filter(date__lt=self.session.date).order_by('-date')
        for prev_session in previous_sessions:
            try:
                return Vote.objects.get(user=self.user, card=self.card, session=prev_session)
            except Vote.DoesNotExist:
                continue
        return None
    
    def has_improved(self):
        """Check if this vote shows improvement compared to the previous one"""
        previous_vote = self.get_previous_vote()
        if not previous_vote:
            return None
        
        # Convert vote values to numeric scores
        score_map = {'green': 3, 'amber': 2, 'red': 1}
        current_score = score_map.get(self.value)
        previous_score = score_map.get(previous_vote.value)
        
        return current_score > previous_score

class TeamSummary(models.Model):
    VOTE_CHOICES = (
        ('green', 'Green'),
        ('amber', 'Amber'),
        ('red', 'Red'),
    )
    PROGRESS_CHOICES = (
        ('better', 'Better'),
        ('same', 'Same'),
        ('worse', 'Worse'),
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    card = models.ForeignKey(HealthCheckCard, on_delete=models.CASCADE)
    average_vote = models.CharField(max_length=5, choices=VOTE_CHOICES)
    progress_summary = models.CharField(max_length=6, choices=PROGRESS_CHOICES)
    green_percentage = models.FloatField(default=0)
    amber_percentage = models.FloatField(default=0)
    red_percentage = models.FloatField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('team', 'card', 'session')
        ordering = ['-session__date']
    
    def __str__(self):
        return f"{self.team.name} - {self.card.name} - {self.average_vote}"
    
    def get_previous_summary(self):
        """Return the previous summary for the same team and card"""
        previous_sessions = Session.objects.filter(date__lt=self.session.date).order_by('-date')
        for prev_session in previous_sessions:
            try:
                return TeamSummary.objects.get(team=self.team, card=self.card, session=prev_session)
            except TeamSummary.DoesNotExist:
                continue
        return None
    
    def calculate_trend(self):
        """Calculate trend based on previous sessions"""
        previous_summary = self.get_previous_summary()
        if not previous_summary:
            return None
        
        # Convert vote values to numeric scores
        score_map = {'green': 3, 'amber': 2, 'red': 1}
        current_score = score_map.get(self.average_vote)
        previous_score = score_map.get(previous_summary.average_vote)
        
        if current_score > previous_score:
            return 'improving'
        elif current_score < previous_score:
            return 'declining'
        else:
            return 'stable'

class DepartmentSummary(models.Model):
    VOTE_CHOICES = (
        ('green', 'Green'),
        ('amber', 'Amber'),
        ('red', 'Red'),
    )
    PROGRESS_CHOICES = (
        ('better', 'Better'),
        ('same', 'Same'),
        ('worse', 'Worse'),
    )
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    card = models.ForeignKey(HealthCheckCard, on_delete=models.CASCADE)
    average_vote = models.CharField(max_length=5, choices=VOTE_CHOICES)
    progress_summary = models.CharField(max_length=6, choices=PROGRESS_CHOICES)
    green_percentage = models.FloatField(default=0)
    amber_percentage = models.FloatField(default=0)
    red_percentage = models.FloatField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('department', 'card', 'session')
        ordering = ['-session__date']
    
    def __str__(self):
        return f"{self.department.name} - {self.card.name} - {self.average_vote}"
    
    def get_previous_summary(self):
        """Return the previous summary for the same department and card"""
        previous_sessions = Session.objects.filter(date__lt=self.session.date).order_by('-date')
        for prev_session in previous_sessions:
            try:
                return DepartmentSummary.objects.get(department=self.department, card=self.card, session=prev_session)
            except DepartmentSummary.DoesNotExist:
                continue
        return None
    
    def calculate_trend(self):
        """Calculate trend based on previous sessions"""
        previous_summary = self.get_previous_summary()
        if not previous_summary:
            return None
        
        # Convert vote values to numeric scores
        score_map = {'green': 3, 'amber': 2, 'red': 1}
        current_score = score_map.get(self.average_vote)
        previous_score = score_map.get(previous_summary.average_vote)
        
        if current_score > previous_score:
            return 'improving'
        elif current_score < previous_score:
            return 'declining'
        else:
            return 'stable'

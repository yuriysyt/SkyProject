
"""Django models for the Health Check System.

This module defines the data models that form the core of the Health Check System. 
The system is designed around a hierarchical organizational structure (Departments and Teams)
with users who participate in periodic health check sessions by voting on various health check
categories (cards) using a traffic light system (green, amber, red).

Key components:
- User: Extended Django user model with role-based permissions
- Department/Team: Organizational hierarchy models
- Session: Time periods for conducting health checks
- HealthCheckCard: Categories to be evaluated in health checks
- Vote: Individual user evaluations for each card in a session
- TeamSummary/DepartmentSummary: Aggregated metrics at team and department levels

The models implement various methods for calculating trends, permissions, and aggregated statistics.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class User(AbstractUser):
    """
    Extended User model that inherits from Django's AbstractUser.
    
    This model adds role-based permissions and organizational hierarchy relationships
    to the standard Django user model. Users are assigned specific roles that determine
    their access levels and permissions within the health check system. Users can also
    be associated with specific teams and departments in the organizational structure.
    
    The role hierarchy from lowest to highest access level is:
    1. Engineer - Can vote on health check cards for their team
    2. Team Leader - Can manage their team and view team summaries
    3. Department Leader - Can manage teams in their department and view department summaries
    4. Senior Manager - Can view organization-wide data and all departments
    5. Admin - Has full system access and configuration abilities
    
    This model is used extensively throughout the application for authentication,
    authorization, and determining what data each user can access and modify.
    """
    # Role choices tuple defining all possible user roles in the system
    # These roles determine permissions and access levels
    ROLES = (
        ('engineer', 'Engineer'),  # Base role - can submit votes only
        ('team_leader', 'Team Leader'),  # Can manage team and view team summaries
        ('department_leader', 'Department Leader'),  # Can manage department and view department summaries
        ('senior_manager', 'Senior Manager'),  # Can view all departments and organization-wide data
        ('admin', 'Admin'),  # Has full system access
    )
    # User's role in the organization - determines permissions and access levels
    role = models.CharField(max_length=20, choices=ROLES)
    
    # Department relationship - users can belong to a department
    # SET_NULL ensures users aren't deleted if their department is deleted
    department = models.ForeignKey(
        'Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Team relationship - users can belong to a team within their department
    # SET_NULL ensures users aren't deleted if their team is deleted
    team = models.ForeignKey(
        'Team', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Optional profile picture for user accounts
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    # Optional biographical information for user profiles
    bio = models.TextField(blank=True, null=True)

    # Override the default groups field to avoid conflicts with AbstractUser
    # Custom related_name prevents reverse accessor conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='custom_user_set',  # Custom related_name to avoid conflicts
        related_query_name='custom_user',
    )
    
    # Override the default permissions field to avoid conflicts with AbstractUser
    # Custom related_name prevents reverse accessor conflicts
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',  # Custom related_name to avoid conflicts
        related_query_name='custom_user',
    )
    
    def __str__(self):
        """
        String representation of the User model.
        
        Returns:
            String with username and display version of role
        """
        return f"{self.username} ({self.get_role_display()})"
    
    def get_recent_votes(self):
        """
        Return user's votes from the most recent active session.
        
        This method finds the most recent active session and returns all votes
        submitted by this user for that session. Used in dashboard and reporting
        views to show users their recent contributions.
        
        Returns:
            QuerySet of Vote objects or empty QuerySet if no active session exists
        """
        # Find the most recent active session
        recent_session = Session.objects.filter(is_active=True).order_by('-date').first()
        if recent_session:
            # Return all votes by this user in that session
            return Vote.objects.filter(user=self, session=recent_session)
        # Return empty QuerySet if no active session exists
        return Vote.objects.none()
    
    def has_voted_in_session(self, session):
        """
        Check if user has submitted any votes in a specific session.
        
        This method is used to track participation and identify users who
        haven't yet contributed to a health check session. Used in team
        detail views and participation reports.
        
        Args:
            session: Session object to check for votes
            
        Returns:
            Boolean indicating whether the user has voted in the session
        """
        return Vote.objects.filter(user=self, session=session).exists()
    
    def can_manage_team(self, team):
        """
        Check if user has permission to manage the given team.
        
        Implements role-based access control for team management:
        - Admins and senior managers can manage any team
        - Department leaders can manage teams in their department
        - Team leaders can only manage their own team
        - Engineers cannot manage any team
        
        This method is used in views to control access to team management
        functions like editing team details or viewing team summaries.
        
        Args:
            team: Team object to check management permission for
            
        Returns:
            Boolean indicating whether the user can manage the team
        """
        # Admins and senior managers can manage any team
        if self.role == 'admin' or self.role == 'senior_manager':
            return True
        # Department leaders can manage teams in their department
        if self.role == 'department_leader' and team.department == self.department:
            return True
        # Team leaders can only manage their own team
        if self.role == 'team_leader' and team == self.team:
            return True
        # All other roles (engineers) cannot manage teams
        return False
    
    def can_view_department_summary(self, department):
        """
        Check if user has permission to view a department's summary data.
        
        Implements role-based access control for department data:
        - Admins and senior managers can view any department
        - Department leaders can only view their own department
        - Team leaders and engineers cannot view department summaries
        
        This method is used in views to control access to department summary
        pages and department-level reports.
        
        Args:
            department: Department object to check viewing permission for
            
        Returns:
            Boolean indicating whether the user can view the department summary
        """
        # Admins and senior managers can view any department
        if self.role == 'admin' or self.role == 'senior_manager':
            return True
        # Department leaders can only view their own department
        if self.role == 'department_leader' and department == self.department:
            return True
        # All other roles cannot view department summaries
        return False

class Department(models.Model):
    """
    Department model representing a high-level organizational unit.
    
    Departments are the top level of the organizational hierarchy in the health check system.
    Each department can contain multiple teams, and users can be assigned to a department.
    Department-level summaries aggregate health check data across all teams within the department,
    providing leadership with a high-level view of organizational health.
    
    This model is primarily used for organizing teams and users, and for generating
    department-level reports and dashboards for department leaders and senior management.
    """
    # Department name - displayed in UI and reports
    name = models.CharField(max_length=100)
    
    # Optional description of the department's purpose or scope
    description = models.TextField(blank=True, null=True)
    
    # Timestamps for auditing and sorting
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        """
        String representation of the Department model.
        
        Returns:
            Department name as string
        """
        return self.name
    
    def get_teams(self):
        """
        Get all teams belonging to this department.
        
        This method retrieves all teams associated with the department,
        used in department detail views and for calculating department-wide metrics.
        
        Returns:
            QuerySet of Team objects belonging to this department
        """
        return Team.objects.filter(department=self)
    
    def get_team_count(self):
        """
        Count the number of teams in this department.
        
        Used in department overview pages and for administrative reporting.
        
        Returns:
            Integer count of teams in this department
        """
        return self.get_teams().count()
    
    def get_user_count(self):
        """
        Count the number of users assigned to this department.
        
        This method counts all users who have this department assigned,
        regardless of their team assignment. Used in department overview
        pages and administrative reporting.
        
        Returns:
            Integer count of users in this department
        """
        return User.objects.filter(department=self).count()
    
    def get_recent_summaries(self):
        """
        Get department summaries from the most recent active session.
        
        This method retrieves all department summary objects for this department
        from the most recent active session. Used in dashboard views and reports
        to show current department health status.
        
        Returns:
            QuerySet of DepartmentSummary objects or empty QuerySet if no active session
        """
        # Find the most recent active session
        recent_session = Session.objects.filter(is_active=True).order_by('-date').first()
        if recent_session:
            # Return all summaries for this department in that session
            return DepartmentSummary.objects.filter(department=self, session=recent_session)
        # Return empty QuerySet if no active session exists
        return DepartmentSummary.objects.none()

class Team(models.Model):
    """
    Team model representing a mid-level organizational unit.
    
    Teams are the second level of the organizational hierarchy in the health check system.
    Each team belongs to a department and can have multiple users assigned.
    Team-level summaries aggregate health check data across all users within the team,
    providing team leaders with a view of team health.
    
    This model is primarily used for organizing users and generating team-level reports
    and dashboards for team leaders and department leaders.
    """
    # Team name - displayed in UI and reports
    name = models.CharField(max_length=100)
    
    # Optional team description
    description = models.TextField(blank=True, null=True)
    
    # Department relationship - teams belong to a department
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        """
        String representation of the Team model.
        
        Returns:
            String with team name and its department name in parentheses
        """
        return f"{self.name} ({self.department.name})"
    
    def get_member_count(self):
        """
        Count the number of users assigned to this team.
        
        This method is used in team overview pages, department dashboards,
        and administrative reports to show team sizes and distribution.
        
        Returns:
            Integer count of users assigned to this team
        """
        return User.objects.filter(team=self).count()
    
    def get_members(self):
        """
        Get all users assigned to this team.
        
        This method retrieves all users who have this team assigned,
        used in team detail views, participation tracking, and for
        calculating team-wide metrics and participation rates.
        
        Returns:
            QuerySet of User objects belonging to this team
        """
        return User.objects.filter(team=self)
    
    def get_team_leaders(self):
        """
        Get all users with 'team_leader' role assigned to this team.
        
        This method is used to identify team leaders for notifications,
        report distribution, and access control. Teams may have multiple
        leaders or none at all.
        
        Returns:
            QuerySet of User objects with team_leader role for this team
        """
        return User.objects.filter(team=self, role='team_leader')
    
    def get_latest_health_status(self):
        """
        Calculate the overall health status of the team based on the most recent session.
        
        This method determines the team's overall health status by counting the
        number of red, amber, and green average votes across all health check cards
        in the most recent active session. The status is determined by which color
        has the highest count, with a bias toward green if counts are equal.
        
        This is used in dashboards and reports to provide a high-level view of
        team health without requiring detailed examination of individual metrics.
        
        Returns:
            String ('red', 'amber', or 'green') representing overall health status,
            or None if no data is available for the latest session
        """
        # Find the most recent active session
        latest_session = Session.objects.filter(is_active=True).order_by('-date').first()
        if not latest_session:
            return None
        
        # Get all team summaries for this team in the latest session
        team_summaries = TeamSummary.objects.filter(team=self, session=latest_session)
        if not team_summaries.exists():
            return None
        
        # Count votes by color
        red_count = team_summaries.filter(average_vote='red').count()
        amber_count = team_summaries.filter(average_vote='amber').count()
        green_count = team_summaries.filter(average_vote='green').count()
        
        # Determine overall status based on which color has the highest count
        if red_count > amber_count and red_count > green_count:
            return 'red'
        elif amber_count > red_count and amber_count > green_count:
            return 'amber'
        elif green_count > 0:
            return 'green'
        return None

class Session(models.Model):
    """
    Session model representing a time period for health check voting.
    
    Sessions are time-bounded periods when users can submit votes for health check cards.
    Each session has a specific date and can be active or inactive. Only one session
    should be active at a time, and votes are always associated with a specific session.
    
    Sessions enable historical tracking of health check data over time, allowing for
    trend analysis and progress tracking. They also provide a mechanism to control
    when voting is open or closed to users.
    
    This model is central to the health check system's temporal organization and is
    referenced by votes, team summaries, and department summaries.
    """
    # Session name for display in UI and reports
    name = models.CharField(max_length=100, default="Health Check Session")
    
    # Date when this session occurs/occurred
    date = models.DateField()
    
    # Detailed description of the session's purpose or focus
    description = models.TextField()
    
    # Flag indicating whether voting is currently open for this session
    # Only one session should be active at a time
    is_active = models.BooleanField(default=True)
    
    # Timestamp for when the session was created
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        """
        String representation of the Session model.
        
        Returns:
            String with session name and date
        """
        return f"{self.name} - {self.date}"
    
    class Meta:
        """
        Meta options for the Session model.
        
        - ordering: Sessions are ordered by date in descending order (newest first)
        """
        ordering = ['-date']
    
    def get_participation_rate(self, team=None):
        """
        Calculate the participation rate for this session.
        
        This method calculates what percentage of eligible users have submitted
        at least one vote in this session. It can be filtered by team to get
        team-specific participation rates.
        
        Used in dashboards and reports to track engagement and identify teams
        or individuals who haven't participated.
        
        Args:
            team: Optional Team object to filter participation by team
            
        Returns:
            Float representing percentage (0-100) of eligible users who have participated
        """
        if team:
            # Calculate participation rate for a specific team
            eligible_users = User.objects.filter(team=team).count()
            if eligible_users == 0:
                return 0  # Avoid division by zero
            # Count distinct users who have voted in this session from this team
            participants = Vote.objects.filter(session=self, user__team=team).values('user').distinct().count()
            return (participants / eligible_users) * 100
        else:
            # Calculate participation rate across all users
            eligible_users = User.objects.all().count()
            if eligible_users == 0:
                return 0  # Avoid division by zero
            # Count distinct users who have voted in this session
            participants = Vote.objects.filter(session=self).values('user').distinct().count()
            return (participants / eligible_users) * 100
    
    def is_complete(self):
        """
        Check if all eligible users have submitted votes in this session.
        
        This method determines if the session is complete by checking if all
        engineers and team leaders have submitted at least one vote. Senior managers,
        department leaders, and admins are not counted as they typically don't
        participate in voting.
        
        Used to determine if a session can be closed or if reminders need to be
        sent to non-participating users.
        
        Returns:
            Boolean indicating whether all eligible users have participated
        """
        # Only engineers and team leaders are expected to vote
        eligible_users = User.objects.filter(role__in=['engineer', 'team_leader']).count()
        # Count distinct users who have voted in this session
        participants = Vote.objects.filter(session=self).values('user').distinct().count()
        # Session is complete when all eligible users have participated
        return eligible_users == participants

class HealthCheckCard(models.Model):
    """
    HealthCheckCard model representing a category or aspect to be evaluated in health checks.
    
    Health check cards define the specific areas that users vote on during health check sessions.
    Examples might include "Team Morale", "Technical Debt", "Delivery Pace", etc. Each card
    receives votes from users using the traffic light system (green, amber, red).
    
    Cards can be activated or deactivated to control which aspects are evaluated in
    health checks. They also have an ordering to ensure consistent presentation across
    the application.
    
    This model is a core component of the health check system as it defines what
    aspects of team health are being measured and tracked over time.
    """
    # Name of the health check category (e.g., "Team Morale", "Technical Debt")
    name = models.CharField(max_length=100)
    
    # Detailed description of what this category measures and how to evaluate it
    description = models.TextField()
    
    # Optional icon identifier for UI display (e.g., FontAwesome icon name)
    icon = models.CharField(max_length=50, blank=True, null=True)
    
    # Position in the display order of cards (lower numbers appear first)
    order = models.PositiveIntegerField(default=0)
    
    # Flag indicating whether this card is currently in use
    # Inactive cards won't appear in voting forms but historical data is preserved
    active = models.BooleanField(default=True)
    
    def __str__(self):
        """
        String representation of the HealthCheckCard model.
        
        Returns:
            Card name as string
        """
        return self.name
    
    class Meta:
        """
        Meta options for the HealthCheckCard model.
        
        - ordering: Cards are ordered by their order field (ascending)
          to ensure consistent display order in forms and reports
        """
        ordering = ['order']
    
    def get_vote_distribution(self, session=None):
        """
        Calculate the distribution of votes across traffic light values for this card.
        
        This method calculates the percentage distribution of green, amber, and red
        votes for this card. It can be filtered by session to get the distribution
        for a specific time period.
        
        Used in dashboards, reports, and visualizations to show how votes are
        distributed for this particular aspect of team health.
        
        Args:
            session: Optional Session object to filter votes by session
            
        Returns:
            Dictionary with keys 'green', 'amber', 'red' and percentage values (0-100)
        """
        # Get all votes for this card, optionally filtered by session
        votes = Vote.objects.filter(card=self)
        if session:
            votes = votes.filter(session=session)
        
        # Count total votes
        total = votes.count()
        if total == 0:
            # Return zeros if no votes exist
            return {'green': 0, 'amber': 0, 'red': 0}
        
        # Count votes by color
        green = votes.filter(value='green').count()
        amber = votes.filter(value='amber').count()
        red = votes.filter(value='red').count()
        
        # Calculate percentages
        return {
            'green': (green / total) * 100,
            'amber': (amber / total) * 100,
            'red': (red / total) * 100
        }

class Vote(models.Model):
    """
    Vote model representing an individual user's evaluation of a health check card.
    
    Votes are the core data points in the health check system. Each vote represents
    a single user's assessment of a specific health check card (category) during a
    particular session. Votes use a traffic light system (green, amber, red) to indicate
    the health status of that category, along with a progress indicator (better, same, worse)
    to track trends over time.
    
    The combination of user, card, and session must be unique, ensuring that each user
    can only vote once per card per session. Votes can include optional comments to
    provide context or explanations for the chosen status.
    
    This model is used extensively in calculating team and department summaries,
    tracking progress over time, and generating reports and visualizations.
    """
    # Traffic light voting system choices
    VOTE_CHOICES = (
        ('green', 'Green'),  # Good/healthy status
        ('amber', 'Amber'),  # Caution/moderate issues
        ('red', 'Red'),      # Poor/critical issues
    )
    
    # Progress tracking choices to indicate trend direction
    PROGRESS_CHOICES = (
        ('better', 'Better'),  # Improving since last session
        ('same', 'Same'),      # No change since last session
        ('worse', 'Worse'),    # Deteriorating since last session
    )
    
    # User who submitted this vote
    # CASCADE ensures votes are deleted if the user is deleted
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # The health check category this vote is assessing
    # CASCADE ensures votes are deleted if the card is deleted
    card = models.ForeignKey(HealthCheckCard, on_delete=models.CASCADE)
    
    # The session during which this vote was submitted
    # CASCADE ensures votes are deleted if the session is deleted
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    
    # The traffic light value selected by the user
    value = models.CharField(max_length=5, choices=VOTE_CHOICES)
    
    # The user's assessment of progress since the last session
    progress_note = models.CharField(max_length=6, choices=PROGRESS_CHOICES)
    
    # Optional comment providing context or explanation for the vote
    comment = models.TextField(blank=True, null=True)
    
    # Timestamps for auditing and sorting
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        """
        Meta options for the Vote model.
        
        - unique_together: Ensures a user can only vote once per card per session
        - ordering: Votes are ordered by creation time (newest first)
        """
        unique_together = ('user', 'card', 'session')
        ordering = ['-created_at']
    
    def __str__(self):
        """
        String representation of the Vote model.
        
        Returns:
            String with username, card name, and vote value
        """
        return f"{self.user.username} - {self.card.name} - {self.value}"
    
    def get_previous_vote(self):
        """
        Find the most recent previous vote by the same user for the same card.
        
        This method searches for the most recent vote from earlier sessions
        by the same user for the same health check card. It's used for trend
        analysis and calculating progress over time.
        
        Returns:
            Vote object from the previous session, or None if no previous vote exists
        """
        # Get all previous sessions ordered by date (newest first)
        previous_sessions = Session.objects.filter(date__lt=self.session.date).order_by('-date')
        
        # Check each previous session for a matching vote
        for prev_session in previous_sessions:
            try:
                return Vote.objects.get(user=self.user, card=self.card, session=prev_session)
            except Vote.DoesNotExist:
                continue
        
        # No previous vote found
        return None
    
    def has_improved(self):
        """
        Check if this vote shows improvement compared to the previous session.
        
        This method compares the current vote value with the value from the
        previous session to determine if there has been an improvement.
        Green is better than amber, which is better than red.
        
        Used in progress tracking, trend analysis, and highlighting improvements
        or deteriorations in team health.
        
        Returns:
            Boolean indicating improvement, or None if no previous vote exists
        """
        # Get the previous vote by this user for this card
        previous_vote = self.get_previous_vote()
        if not previous_vote:
            return None  # Can't determine improvement without a previous vote
        
        # Convert vote values to numeric scores for comparison
        # Higher numbers are better: green (3) > amber (2) > red (1)
        score_map = {'green': 3, 'amber': 2, 'red': 1}
        current_score = score_map.get(self.value)
        previous_score = score_map.get(previous_vote.value)
        
        return current_score > previous_score


class TeamSummary(models.Model):
    """
    TeamSummary model representing aggregated health check data for a team.
    
    This model aggregates individual votes into team-level metrics for each
    health check card in a session. It stores the average vote value (green, amber, red)
    across all team members, as well as the percentage distribution of votes.
    
    Team summaries are automatically calculated after all team members have voted
    in a session, or when the session is closed. They provide team leaders and
    department leaders with an overview of team health across different categories.
    
    This model is used in dashboards, reports, and trend analysis to track team health
    over time, identify areas that need attention, and compare health across teams.
    """
    # Reference the same choices as Vote model for consistency
    VOTE_CHOICES = Vote.VOTE_CHOICES
    PROGRESS_CHOICES = Vote.PROGRESS_CHOICES
    
    # Core relationships - each summary is for a specific team, card, and session
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    card = models.ForeignKey(HealthCheckCard, on_delete=models.CASCADE)
    
    # Summary data - aggregated from individual votes
    average_vote = models.CharField(max_length=5, choices=VOTE_CHOICES)
    progress_summary = models.CharField(max_length=6, choices=PROGRESS_CHOICES)
    
    # Percentage distribution of votes by value
    green_percentage = models.FloatField(default=0)
    amber_percentage = models.FloatField(default=0)
    red_percentage = models.FloatField(default=0)
    
    # Timestamps for tracking when summaries are created and updated
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        """
        Meta options for the TeamSummary model.
        
        - unique_together: Ensures each team has only one summary per card per session
        - ordering: Summaries are ordered by session date, newest first
        """
        unique_together = ('team', 'card', 'session')
        ordering = ['-session__date']
    
    def __str__(self):
        """
        String representation of the TeamSummary model.
        
        Returns:
            String with team name, card name, and average vote value
        """
        return f"{self.team.name} - {self.card.name} - {self.average_vote}"
    
    def get_previous_summary(self):
        """
        Find the most recent previous summary for the same team and card.
        
        This method searches for the most recent team summary from earlier sessions
        for the same team and health check card. It's used for trend analysis and
        calculating progress over time.
        
        Returns:
            TeamSummary object from the previous session, or None if no previous summary exists
        """
        # Get all previous sessions ordered by date (newest first)
        previous_sessions = Session.objects.filter(date__lt=self.session.date).order_by('-date')
        
        # Check each previous session for a matching summary
        for prev_session in previous_sessions:
            try:
                return TeamSummary.objects.get(team=self.team, card=self.card, session=prev_session)
            except TeamSummary.DoesNotExist:
                continue
        
        # No previous summary found
        return None
    
    def calculate_trend(self):
        """
        Calculate the health trend compared to the previous session.
        
        This method compares the current average vote with the average vote from the
        previous session to determine if the team's health in this category is improving,
        declining, or stable.
        
        Used in dashboards, reports, and visualizations to highlight trends and
        changes in team health over time.
        
        Returns:
            String ('improving', 'declining', or 'stable') indicating the trend,
            or None if no previous summary exists
        """
        # Get the previous summary for this team and card
        previous_summary = self.get_previous_summary()
        if not previous_summary:
            return None  # Can't determine trend without a previous summary
        
        # Convert vote values to numeric scores for comparison
        # Higher numbers are better: green (3) > amber (2) > red (1)
        score_map = {'green': 3, 'amber': 2, 'red': 1}
        current_score = score_map.get(self.average_vote)
        previous_score = score_map.get(previous_summary.average_vote)
        
        # Determine trend based on score comparison
        if current_score > previous_score:
            return 'improving'  # Current score is higher than previous score
        elif current_score < previous_score:
            return 'declining'  # Current score is lower than previous score
        else:
            return 'stable'     # Current score is the same as previous score

class DepartmentSummary(models.Model):
    """
    DepartmentSummary model representing aggregated health check data for a department.
    
    This model aggregates team-level summaries into department-level metrics for each
    health check card in a session. It stores the average vote value (green, amber, red)
    across all teams in the department, as well as the percentage distribution of votes.
    
    Department summaries are automatically calculated after all team summaries have been
    generated for a session, or when the session is closed. They provide department leaders
    and senior management with an overview of department health across different categories.
    
    This model is used in dashboards, reports, and trend analysis to track department health
    over time, identify areas that need attention, and compare health across departments.
    """
    # Traffic light voting system choices (same as Vote model)
    VOTE_CHOICES = (
        ('green', 'Green'),  # Good/healthy status
        ('amber', 'Amber'),  # Caution/moderate issues
        ('red', 'Red'),      # Poor/critical issues
    )
    
    # Progress tracking choices (same as Vote model)
    PROGRESS_CHOICES = (
        ('better', 'Better'),  # Improving since last session
        ('same', 'Same'),      # No change since last session
        ('worse', 'Worse'),    # Deteriorating since last session
    )
    
    # The department this summary is for
    # CASCADE ensures summaries are deleted if the department is deleted
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    
    # The session this summary is for
    # CASCADE ensures summaries are deleted if the session is deleted
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    
    # The health check card this summary is for
    # CASCADE ensures summaries are deleted if the card is deleted
    card = models.ForeignKey(HealthCheckCard, on_delete=models.CASCADE)
    
    # The calculated average vote value for this department, card, and session
    average_vote = models.CharField(max_length=5, choices=VOTE_CHOICES)
    
    # The calculated progress trend compared to the previous session
    progress_summary = models.CharField(max_length=6, choices=PROGRESS_CHOICES)
    
    # Percentage distribution of votes across traffic light values
    # These percentages should sum to 100
    green_percentage = models.FloatField(default=0)  # Percentage of green votes
    amber_percentage = models.FloatField(default=0)  # Percentage of amber votes
    red_percentage = models.FloatField(default=0)    # Percentage of red votes
    
    # Timestamps for auditing and sorting
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        """
        Meta options for the DepartmentSummary model.
        
        - unique_together: Ensures only one summary per department, card, and session combination
        - ordering: Summaries are ordered by session date (newest first)
        """
        unique_together = ('department', 'card', 'session')
        ordering = ['-session__date']
    
    def __str__(self):
        """
        String representation of the DepartmentSummary model.
        
        Returns:
            String with department name, card name, and average vote value
        """
        return f"{self.department.name} - {self.card.name} - {self.average_vote}"
    
    def get_previous_summary(self):
        """
        Find the most recent previous summary for the same department and card.
        
        This method searches for the most recent department summary from earlier sessions
        for the same department and health check card. It's used for trend analysis and
        calculating progress over time.
        
        Returns:
            DepartmentSummary object from the previous session, or None if no previous summary exists
        """
        # Get all previous sessions ordered by date (newest first)
        previous_sessions = Session.objects.filter(date__lt=self.session.date).order_by('-date')
        
        # Check each previous session for a matching summary
        for prev_session in previous_sessions:
            try:
                return DepartmentSummary.objects.get(department=self.department, card=self.card, session=prev_session)
            except DepartmentSummary.DoesNotExist:
                continue
        
        # No previous summary found
        return None
    
    def calculate_trend(self):
        """
        Calculate the health trend compared to the previous session.
        
        This method compares the current average vote with the average vote from the
        previous session to determine if the department's health in this category is
        improving, declining, or stable.
        
        Used in dashboards, reports, and visualizations to highlight trends and
        changes in department health over time.
        
        Returns:
            String ('improving', 'declining', or 'stable') indicating the trend,
            or None if no previous summary exists
        """
        # Get the previous summary for this department and card
        previous_summary = self.get_previous_summary()
        if not previous_summary:
            return None  # Can't determine trend without a previous summary
        
        # Convert vote values to numeric scores for comparison
        # Higher numbers are better: green (3) > amber (2) > red (1)
        score_map = {'green': 3, 'amber': 2, 'red': 1}
        current_score = score_map.get(self.average_vote)
        previous_score = score_map.get(previous_summary.average_vote)
        
        # Determine trend based on score comparison
        if current_score > previous_score:
            return 'improving'  # Current score is higher than previous score
        elif current_score < previous_score:
            return 'declining'  # Current score is lower than previous score
        else:
            return 'stable'     # Current score is the same as previous score

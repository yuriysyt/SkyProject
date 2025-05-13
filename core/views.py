from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db.models import Count, Avg, Case, When, F, FloatField, Q, Sum
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
import json

from .models import (
    User, Team, Department, Session, HealthCheckCard, Vote, 
    TeamSummary, DepartmentSummary
)
from .forms import (
    UserRegistrationForm, UserProfileForm, VoteForm, SessionForm,
    TeamForm, DepartmentForm, HealthCheckCardForm, SessionSelectionForm,
    DateRangeForm, TeamSelectionForm
)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to Health Check System.')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'core/register.html', {'form': form})

@login_required
def dashboard(request):
    """
    Display the main dashboard customized for the user's role.
    
    This view serves as the central hub of the application, showing different
    content based on the user's role (engineer, team leader, department leader,
    or senior manager). Each role sees a tailored view with relevant information
    and actions.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Content is filtered based on user's role and permissions
    
    Args:
        request: HttpRequest object containing metadata about the request
        
    Returns:
        HttpResponse: Renders the dashboard with role-specific context
        
    Template:
        core/dashboard.html - Receives context with role-specific data
    """
    user = request.user
    today = timezone.now().date()
    
    # Get active sessions - common data needed for all user roles
    active_sessions = Session.objects.filter(is_active=True)
    
    # Initialize context with common data
    context = {
        'user': user,
        'active_sessions': active_sessions,
        'today': today,
    }
    
    # Load role-specific data based on user role
    if user.role == 'engineer':
        # Engineer dashboard shows their team's health check cards and voting options
        if user.team:
            # Get all active health check cards for voting
            # These are the categories (e.g., Delivery, Quality) that users vote on
            cards = HealthCheckCard.objects.filter(active=True)
            
            # Get latest session for current voting
            # Sessions represent time periods (e.g., weekly, monthly) for health checks
            # Using first() assumes sessions are ordered by recency (newest first)
            latest_session = Session.objects.first()
            
            # Get user's votes for latest session to show their previous choices
            # This allows users to see and potentially update their previous votes
            user_votes = {}
            if latest_session:
                votes = Vote.objects.filter(
                    user=user,
                    session=latest_session
                )
                # Create a dictionary mapping card IDs to vote objects for easy access in template
                user_votes = {vote.card_id: vote for vote in votes}
                
            # Team summaries for user's team to show overall team health
            # These are aggregated statistics from all team members' votes
            team_summaries = TeamSummary.objects.filter(team=user.team)
            
            context.update({
                'cards': cards,                     # Health check categories to vote on
                'latest_session': latest_session,   # Current active voting session
                'user_votes': user_votes,           # User's previous votes for reference
                'team_summaries': team_summaries,   # Team's overall health metrics
            })
    
    elif user.role == 'team_leader':
        # Team leader dashboard shows team members, team health, and department context
        # Team leaders need more comprehensive data to manage their team effectively
        team = user.team
        department = user.department
        
        if team:
            # Get team members for management and tracking participation
            # This allows team leaders to see who has and hasn't voted
            team_members = User.objects.filter(team=team)
            
            # Get team summaries to monitor overall team health
            # These aggregated statistics help identify trends and issues
            team_summaries = TeamSummary.objects.filter(team=team)
            
            # Get health check cards for team leader's own voting
            # Team leaders also participate in voting like engineers
            cards = HealthCheckCard.objects.filter(active=True)
            
            # Get latest session for current voting period
            latest_session = Session.objects.first()
            
            # Get team leader's own votes to pre-populate forms
            # Team leaders can lead by example by voting first
            user_votes = {}
            if latest_session:
                votes = Vote.objects.filter(
                    user=user,
                    session=latest_session
                )
                user_votes = {vote.card_id: vote for vote in votes}
            
            # Get other teams in the department for comparison
            # This provides context on how the team is performing relative to peers
            other_teams = Team.objects.filter(department=department).exclude(id=team.id)
            
            context.update({
                'team': team,                       # The team being managed
                'team_members': team_members,       # Members for tracking participation
                'team_summaries': team_summaries,   # Aggregated team health metrics
                'other_teams': other_teams,         # Peer teams for comparison
                'cards': cards,                     # Health check categories
                'latest_session': latest_session,   # Current active session
                'user_votes': user_votes,           # Team leader's own votes
            })
        
    elif user.role == 'department_leader':
        # Department leader dashboard shows teams, department health, and organization context
        # Department leaders need broad visibility across multiple teams
        department = user.department
        
        if department:
            # Get teams in department for management and comparison
            # This allows department leaders to identify high and low performing teams
            teams = Team.objects.filter(department=department)
            
            # Get department summaries to monitor overall department health
            # These are aggregated metrics across all teams in the department
            department_summaries = DepartmentSummary.objects.filter(department=department)
            
            # Get team summaries for all teams in department for detailed analysis
            # This allows comparing individual team performance within the department
            team_summaries = TeamSummary.objects.filter(team__department=department)
            
            # Get other departments for organization-wide context
            # This provides perspective on how the department compares to others
            other_departments = Department.objects.exclude(id=department.id)
            
            context.update({
                'department': department,                   # The department being managed
                'teams': teams,                            # Teams within the department
                'department_summaries': department_summaries, # Aggregated department metrics
                'team_summaries': team_summaries,          # Individual team metrics
                'other_departments': other_departments,     # Peer departments for comparison
            })
        
    elif user.role == 'senior_manager':
        # Senior manager dashboard shows organization-wide health and all departments
        # Senior managers need the broadest view of the entire organization
        
        # Get all departments for organization-wide management
        # This provides a complete view of all organizational units
        departments = Department.objects.all()
        
        # Get all team summaries for detailed analysis
        # This allows drilling down to specific teams when needed
        team_summaries = TeamSummary.objects.all()
        
        # Get all department summaries for organization-wide health monitoring
        # This provides high-level metrics across the entire organization
        department_summaries = DepartmentSummary.objects.all()
        
        context.update({
            'departments': departments,               # All departments in the organization
            'team_summaries': team_summaries,         # All team metrics for detailed analysis
            'department_summaries': department_summaries, # All department metrics for overview
        })
    
    # Render the dashboard template with the role-specific context
    # The template will adapt its display based on the provided context
    return render(request, 'core/dashboard.html', context)

@login_required
def profile(request):
    """
    Handle user profile viewing and editing.
    
    This view allows users to view and update their profile information
    including personal details, team/department assignments, and preferences.
    The form data is processed and saved to the User model when submitted.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Only allows editing of the authenticated user's own profile
        - Handles file uploads securely through Django's form system
    
    Args:
        request: HttpRequest object containing metadata about the request
        
    Returns:
        HttpResponse: Renders the profile form or redirects after successful update
        
    Template:
        core/profile.html - Receives the profile form instance
        
    Form:
        UserProfileForm from forms.py - Provides fields for user profile editing
    """
    if request.method == 'POST':
        # Process submitted profile form with file upload support
        # The instance parameter ensures we're updating the existing user
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            # Save the updated profile information to the database
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')  # Redirect back to profile page after update
    else:
        # Display profile form with current user data for GET requests
        # Pre-populates the form with the user's existing information
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'core/profile.html', {'form': form})

@login_required
def change_password(request):
    """
    Handle user password changes.
    
    This view allows users to change their account password securely.
    It uses Django's built-in PasswordChangeForm and maintains the user's
    session after password change to prevent automatic logout.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Uses Django's secure password change mechanism with validation
        - Maintains session authentication hash to prevent session invalidation
        - Password requirements enforced by Django's password validators
    
    Args:
        request: HttpRequest object containing metadata about the request
        
    Returns:
        HttpResponse: Renders the password change form or redirects after success
        
    Template:
        core/change_password.html - Receives the password change form
        
    Form:
        PasswordChangeForm from django.contrib.auth.forms - Handles secure password changing
    """
    if request.method == 'POST':
        # Process submitted password change form
        # First parameter is the user whose password is being changed
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            # Save the new password to the database
            user = form.save()
            # Important: update session to prevent automatic logout after password change
            # This maintains the user's authenticated state with the new password
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')  # Redirect to profile page after successful change
        else:
            # Display error message if form validation fails
            messages.error(request, 'Please correct the errors below.')
    else:
        # Display empty password change form for GET requests
        form = PasswordChangeForm(request.user)
    return render(request, 'core/change_password.html', {'form': form})

@login_required
def vote(request, session_id, card_id):
    """
    Handle individual vote submission for a specific health check card.
    
    This view allows engineers and team leaders to submit votes for a specific
    health check card in a specific session. It handles both displaying the
    voting form and processing submitted votes.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Validates user role permissions (engineer or team leader only)
        - Validates session is active before allowing votes
        - Validates user has an assigned team
    
    Args:
        request: HttpRequest object containing metadata about the request
        session_id: ID of the session being voted on
        card_id: ID of the health check card being voted on
        
    Returns:
        HttpResponse: Renders the voting form or redirects after successful vote
        
    Template:
        core/vote.html - Receives the voting form and context
        
    Database:
        - Reads from Session, HealthCheckCard, and Vote models
        - Creates or updates Vote records
        - Triggers team summary updates via update_team_summary()
    """
    # Get session and card objects or return 404 if not found
    # This ensures the requested session and card exist before proceeding
    session = get_object_or_404(Session, id=session_id)
    card = get_object_or_404(HealthCheckCard, id=card_id)
    
    # Check if user is engineer or team leader - only these roles can vote
    # This enforces role-based access control for voting functionality
    if request.user.role not in ['engineer', 'team_leader']:
        messages.error(request, 'Only engineers and team leaders can vote.')
        return redirect('dashboard')
    
    # Check if user has a team - voting is team-based
    # Votes contribute to team health metrics, so team assignment is required
    if not request.user.team:
        messages.error(request, 'You must be assigned to a team to vote.')
        return redirect('dashboard')
    
    # Check if session is active - prevent voting on closed sessions
    # This ensures votes are only collected during the designated time period
    if not session.is_active:
        messages.error(request, 'This session is no longer active.')
        return redirect('dashboard')
    
    # Get existing vote or create new one - allows updating previous votes
    # This supports both initial voting and revising previous votes
    try:
        vote = Vote.objects.get(user=request.user, session=session, card=card)
    except Vote.DoesNotExist:
        vote = None
    
    if request.method == 'POST':
        # Process submitted vote form with validation
        form = VoteForm(request.POST, instance=vote)
        if form.is_valid():
            # Save vote but don't commit to DB yet (commit=False)
            # This allows us to set additional fields before saving
            vote = form.save(commit=False)
            # Set relationships to ensure data integrity
            vote.user = request.user
            vote.session = session
            vote.card = card
            vote.save()
            
            # Update team summary statistics based on this vote
            # This ensures team-level aggregations stay current
            update_team_summary(request.user.team, session, card)
            
            messages.success(request, 'Vote submitted successfully!')
            return redirect('dashboard')
    else:
        # Display vote form with existing vote data if available
        # This pre-populates the form for vote updates
        form = VoteForm(instance=vote)
    
    # Render the voting form with all necessary context
    return render(request, 'core/vote.html', {
        'form': form,          # The voting form (empty or pre-populated)
        'session': session,    # Current session information
        'card': card,          # Health check card being voted on
        'vote': vote           # Existing vote data if available
    })

@login_required
def vote_all(request, session_id):
    """
    Display form for voting on all health check cards at once.
    
    This view prepares a comprehensive voting form that allows users to
    vote on all active health check cards in a single submission. It's
    a convenience feature to streamline the voting process compared to
    voting on each card individually.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Validates user role permissions (engineer or team leader only)
        - Validates session is active before allowing votes
        - Validates user has an assigned team
    
    Args:
        request: HttpRequest object containing metadata about the request
        session_id: ID of the session being voted on
        
    Returns:
        HttpResponse: Renders the comprehensive voting form
        
    Template:
        core/vote_all.html - Receives context with cards and existing votes
        
    Database:
        - Reads from Session, HealthCheckCard, and Vote models
        - Does not write to database (submission handled by vote_all_submit)
    """
    # Get session object or return 404 if not found
    # This ensures the requested session exists before proceeding
    session = get_object_or_404(Session, id=session_id)
    
    # Check if user is engineer or team leader - only these roles can vote
    # This enforces role-based access control for voting functionality
    if request.user.role not in ['engineer', 'team_leader']:
        messages.error(request, 'Only engineers and team leaders can vote.')
        return redirect('dashboard')
    
    # Check if user has a team - voting is team-based
    # Votes contribute to team health metrics, so team assignment is required
    if not request.user.team:
        messages.error(request, 'You must be assigned to a team to vote.')
        return redirect('dashboard')
    
    # Check if session is active - prevent voting on closed sessions
    # This ensures votes are only collected during the designated time period
    if not session.is_active:
        messages.error(request, 'This session is no longer active.')
        return redirect('dashboard')
    
    # Get all active health check cards ordered by their defined sequence
    # The order field ensures cards are displayed in a consistent, logical order
    cards = HealthCheckCard.objects.filter(active=True).order_by('order')
    
    # Get user's existing votes for this session to pre-populate the form
    # This allows users to see and potentially update their previous votes
    user_votes = {}
    votes = Vote.objects.filter(user=request.user, session=session)
    for vote in votes:
        # Create a dictionary mapping card IDs to vote objects for easy access in template
        user_votes[vote.card_id] = vote
    
    # Render the comprehensive voting form with all necessary context
    return render(request, 'core/vote_all.html', {
        'session': session,     # Current session information
        'cards': cards,         # All active health check cards to vote on
        'user_votes': user_votes # User's existing votes for pre-population
    })

@login_required
def vote_all_submit(request, session_id):
    """
    Process submission of votes for all health check cards at once.
    
    This view handles the form submission from vote_all view, processing
    votes for multiple health check cards in a single transaction to ensure
    data consistency. It validates each card's vote data and provides
    feedback on successful and failed submissions.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Validates user role permissions (engineer or team leader only)
        - Validates session is active before allowing votes
        - Validates user has an assigned team
        - Uses database transaction to ensure data integrity
    
    Args:
        request: HttpRequest object containing metadata about the request
        session_id: ID of the session being voted on
        
    Returns:
        HttpResponse: Redirects to dashboard after processing votes
        
    Database:
        - Reads from Session, HealthCheckCard, and Vote models
        - Creates or updates multiple Vote records in a single transaction
        - Triggers team summary updates via update_team_summary()
    """
    # Only process POST requests - redirect others to dashboard
    # This ensures the view only handles form submissions
    if request.method != 'POST':
        return redirect('dashboard')
    
    # Get session object or return 404 if not found
    session = get_object_or_404(Session, id=session_id)
    
    # Check permissions - same security checks as vote_all view
    if request.user.role not in ['engineer', 'team_leader']:
        messages.error(request, 'Only engineers and team leaders can vote.')
        return redirect('dashboard')
    
    if not request.user.team:
        messages.error(request, 'You must be assigned to a team to vote.')
        return redirect('dashboard')
    
    if not session.is_active:
        messages.error(request, 'This session is no longer active.')
        return redirect('dashboard')
    
    # Get card IDs from the form submission
    # The form contains a list of all card IDs being voted on
    card_ids = request.POST.getlist('card_ids')
    
    # Track success and error counts for user feedback
    success_count = 0
    error_count = 0
    
    # Use transaction.atomic to ensure all votes are saved or none are
    # This prevents partial updates if an error occurs mid-process
    with transaction.atomic():
        for card_id in card_ids:
            card_id = int(card_id)  # Convert string ID to integer
            card = get_object_or_404(HealthCheckCard, id=card_id)
            
            # Get form values for this specific card
            # Form field names are dynamically generated with card ID suffix
            value = request.POST.get(f'value_{card_id}')  # Green/Amber/Red vote
            progress_note = request.POST.get(f'progress_{card_id}')  # Better/Same/Worse
            comment = request.POST.get(f'comment_{card_id}', '')  # Optional comment
            
            # Skip if required fields are missing
            # Both value and progress_note are mandatory for a valid vote
            if not value or not progress_note:
                error_count += 1
                continue
            
            # Get existing vote or create new one
            # This supports both initial voting and updating previous votes
            try:
                vote = Vote.objects.get(user=request.user, session=session, card=card)
            except Vote.DoesNotExist:
                vote = Vote(user=request.user, session=session, card=card)
            
            # Update vote with form values
            vote.value = value  # Green/Amber/Red status
            vote.progress_note = progress_note  # Trend direction
            vote.comment = comment  # Additional context
            vote.save()
            
            # Update team summary statistics based on this vote
            # This ensures team-level aggregations stay current
            update_team_summary(request.user.team, session, card)
            
            success_count += 1
    
    # Provide feedback on successful votes
    if success_count > 0:
        messages.success(request, f'Successfully submitted {success_count} votes.')
    
    # Provide feedback on failed votes
    if error_count > 0:
        messages.warning(request, f'Failed to submit {error_count} votes due to missing required fields.')
    
    # Redirect to dashboard after processing all votes
    return redirect('dashboard')

@login_required
def team_summary(request, team_id=None):
    """
    Display team summary data for health check sessions.
    
    This view shows aggregated health check data for a specific team,
    allowing team leaders, department leaders, and senior managers to
    monitor team health over time and identify trends or issues.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Validates user role permissions (team leader or higher)
        - Enforces team access permissions based on user role and relationships
        - Department-based access control for team leaders viewing other teams
    
    Args:
        request: HttpRequest object containing metadata about the request
        team_id: Optional ID of the team to view (defaults to user's team if not specified)
        
    Returns:
        HttpResponse: Renders the team summary view with context data
        HttpResponseForbidden: If user lacks permission to view the requested team
        
    Template:
        core/team_summary.html - Receives team summary context
        
    Database:
        - Reads from Team, Session, TeamSummary, User, and HealthCheckCard models
        - Performs permission-based filtering of data
        - Uses select_related for optimized queries where appropriate
    """
    user = request.user
    
    # Check permissions - only team leaders and above can view summaries
    # This enforces role-based access control at the view level
    if user.role not in ['team_leader', 'department_leader', 'senior_manager']:
        messages.error(request, 'You do not have permission to view team summaries.')
        return redirect('dashboard')
    
    # Get team (either specified or user's team)
    # This supports both direct team access and viewing other teams
    if team_id:
        team = get_object_or_404(Team, id=team_id)
        
        # Check if user has permission to view this specific team
        # Team leaders can only view their own team or teams in their department
        if user.role == 'team_leader' and team != user.team:
            # Department-based access control - team leaders can view other teams in their department
            if team.department != user.department:
                return HttpResponseForbidden('You do not have permission to view this team.')
    else:
        # Default to user's team if no team_id specified
        team = user.team
    
    # Get session selection form to allow filtering by session
    # This allows viewing historical data across different sessions
    session_form = SessionSelectionForm(request.GET or None)
    selected_session = None
    
    if session_form.is_valid():
        # Use the session selected in the form
        selected_session = session_form.cleaned_data['session']
    else:
        # Default to latest session if none selected
        # This assumes sessions are ordered by recency (newest first)
        selected_session = Session.objects.first()
    
    if team and selected_session:
        # Get team summaries for selected session
        # These are the aggregated metrics for the team's health check
        summaries = TeamSummary.objects.filter(team=team, session=selected_session)
        
        # Get team members for context and participation tracking
        # This allows seeing who has contributed to the team's health metrics
        team_members = User.objects.filter(team=team)
        
        # Get health check cards for context and category information
        # These are the categories being evaluated in the health check
        cards = HealthCheckCard.objects.filter(active=True)
        
        # Render the team summary template with comprehensive context
        return render(request, 'core/team_summary.html', {
            'team': team,                     # The team being viewed
            'session': selected_session,      # The selected time period
            'summaries': summaries,           # Aggregated team metrics
            'team_members': team_members,     # Team composition
            'cards': cards,                   # Health check categories
            'session_form': session_form,     # Form for changing session
        })
    
    # Handle case where team or session is missing
    messages.error(request, 'Please select a team and session.')
    return redirect('dashboard')

@login_required
def department_summary(request, department_id=None):
    """
    Display department summary data for health check sessions.
    
    This view shows aggregated health check data for a specific department,
    allowing department leaders and senior managers to monitor department
    health over time and compare teams within the department.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Validates user role permissions (department leader or higher)
        - Enforces department access permissions based on user role
        - Prevents department leaders from viewing other departments
    
    Args:
        request: HttpRequest object containing metadata about the request
        department_id: Optional ID of the department to view (defaults to user's department)
        
    Returns:
        HttpResponse: Renders the department summary view with context data
        HttpResponseForbidden: If user lacks permission to view the requested department
        
    Template:
        core/department_summary.html - Receives department summary context
        
    Database:
        - Reads from Department, Session, DepartmentSummary, Team, TeamSummary, and HealthCheckCard models
        - Performs permission-based filtering of data
        - Uses efficient queries with appropriate filters
    """
    user = request.user
    
    # Check permissions - only department leaders and senior managers can view
    # This enforces role-based access control at the view level
    if user.role not in ['department_leader', 'senior_manager']:
        messages.error(request, 'You do not have permission to view department summaries.')
        return redirect('dashboard')
    
    # Get department (either specified or user's department)
    # This supports both direct department access and viewing via URL parameter
    if department_id:
        department = get_object_or_404(Department, id=department_id)
        
        # Check if user has permission to view this specific department
        # Department leaders can only view their own department
        if user.role == 'department_leader' and department != user.department:
            return HttpResponseForbidden('You do not have permission to view this department.')
    else:
        # Default to user's department if no department_id specified
        department = user.department
    
    # Get session selection form to allow filtering by session
    # This allows viewing historical data across different time periods
    session_form = SessionSelectionForm(request.GET or None)
    selected_session = None
    
    if session_form.is_valid():
        # Use the session selected in the form
        selected_session = session_form.cleaned_data['session']
    else:
        # Default to latest session if none selected
        # This assumes sessions are ordered by recency (newest first)
        selected_session = Session.objects.first()
    
    if department and selected_session:
        # Get department summaries for selected session
        # These are the aggregated metrics for the department's overall health
        dept_summaries = DepartmentSummary.objects.filter(
            department=department, 
            session=selected_session
        )
        
        # Get teams in department for detailed breakdown
        # This allows comparing individual teams within the department
        teams = Team.objects.filter(department=department)
        
        # Get team summaries for all teams in the department
        # This provides team-level metrics for comparison and analysis
        team_summaries = TeamSummary.objects.filter(
            team__in=teams,
            session=selected_session
        )
        
        # Get health check cards for context and category information
        # These are the categories being evaluated in the health check
        cards = HealthCheckCard.objects.filter(active=True)
        
        # Render the department summary template with comprehensive context
        return render(request, 'core/department_summary.html', {
            'department': department,           # The department being viewed
            'session': selected_session,        # The selected time period
            'dept_summaries': dept_summaries,   # Aggregated department metrics
            'teams': teams,                     # Teams within the department
            'team_summaries': team_summaries,   # Team-level metrics for comparison
            'cards': cards,                     # Health check categories
            'session_form': session_form,       # Form for changing session
        })
    
    # Handle case where department or session is missing
    messages.error(request, 'Please select a department and session.')
    return redirect('dashboard')

@login_required
def progress_chart(request):
    """
    Generate and display progress charts for health check data.
    
    This view creates visualizations of health check data over time,
    showing trends and patterns in team and department health. The view
    adapts to the user's role, showing relevant data at the appropriate
    organizational level (individual, team, department, or organization-wide).
    
    The charts include:
    1. Line charts showing Green/Amber/Red trends over time for each health check card
    2. Pie charts showing current status distribution
    3. Pie charts showing progress trend distribution (better/same/worse)
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Filters data based on user role and permissions
        - Enforces hierarchical data access controls
    
    Args:
        request: HttpRequest object containing metadata about the request
        
    Returns:
        HttpResponse: Renders the progress chart view with chart data
        
    Template:
        core/progress_chart.html - Receives JSON-formatted chart data and context
        
    Database:
        - Reads from multiple models including Session, Vote, TeamSummary, and DepartmentSummary
        - Performs complex aggregations and calculations for chart data
        - Optimizes queries with select_related and filtering
    """
    user = request.user
    
    # Get date range selection from form
    # This allows users to customize the time period for trend analysis
    date_form = DateRangeForm(request.GET or None)
    
    if date_form.is_valid():
        # Use user-selected date range from form
        start_date = date_form.cleaned_data['start_date']
        end_date = date_form.cleaned_data['end_date']
    else:
        # Default to last 6 months if no date range specified
        # This provides a reasonable default time window for trend analysis
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=180)
    
    # Get sessions in date range ordered chronologically
    # This provides the time series data points for the x-axis of charts
    sessions = Session.objects.filter(date__range=[start_date, end_date]).order_by('date')
    
    # Initialize chart data structures
    # These will hold the processed data for JavaScript chart rendering
    chart_data = {}  # Will contain final formatted chart data for JS
    session_dates = []  # Will contain formatted dates for x-axis labels
    team_data = None  # Will hold team-level metrics if applicable
    selected_team = None  # Will reference selected team if applicable
    dept_data = None  # Will hold department-level metrics if applicable
    selected_department = None  # Will reference selected department if applicable
    
    # Initialize context with common data
    # This provides the base context that will be enhanced based on user role
    context = {
        'date_form': date_form,         # Form for changing date range
        'start_date': start_date,       # Start of selected time period
        'end_date': end_date,           # End of selected time period
        'sessions': sessions,           # All sessions in the date range
    }
    
    # Get all health check cards for chart labels and data organization
    # Cards are the categories (e.g., Delivery, Quality) being evaluated
    cards = HealthCheckCard.objects.filter(active=True).order_by('order')
    card_names = [card.name for card in cards]  # Extract names for labels
    
    # Create empty datasets structure for chart visualization
    # For each health check card, we create three datasets (green, amber, red)
    # to track the three possible vote values over time
    datasets = []
    for card in cards:
        # Create dataset for green votes with appropriate styling
        # Green represents positive/healthy status
        green_dataset = {
            'label': f'{card.name} - Green',  # Dataset label for chart legend
            'data': [],                       # Will hold percentage/count values
            'backgroundColor': 'rgba(34, 197, 94, 0.2)',  # Light green fill
            'borderColor': 'rgba(34, 197, 94, 1)',        # Green border
            'borderWidth': 2,                 # Border thickness
            'tension': 0.3                    # Curve smoothing for line chart
        }
        # Create dataset for amber votes with appropriate styling
        # Amber represents caution/moderate issues
        amber_dataset = {
            'label': f'{card.name} - Amber',  # Dataset label for chart legend
            'data': [],                       # Will hold percentage/count values
            'backgroundColor': 'rgba(245, 158, 11, 0.2)',  # Light amber fill
            'borderColor': 'rgba(245, 158, 11, 1)',        # Amber border
            'borderWidth': 2,                 # Border thickness
            'tension': 0.3                    # Curve smoothing for line chart
        }
        # Create dataset for red votes with appropriate styling
        # Red represents critical issues/unhealthy status
        red_dataset = {
            'label': f'{card.name} - Red',    # Dataset label for chart legend
            'data': [],                       # Will hold percentage/count values
            'backgroundColor': 'rgba(239, 68, 68, 0.2)',  # Light red fill
            'borderColor': 'rgba(239, 68, 68, 1)',        # Red border
            'borderWidth': 2,                 # Border thickness
            'tension': 0.3                    # Curve smoothing for line chart
        }
        # Add all three datasets to our collection
        # Each card will have three lines on the chart (green, amber, red)
        datasets.extend([green_dataset, amber_dataset, red_dataset])
    
    # Process data based on user role
    if sessions.exists():
        session_dates = [session.date.strftime('%Y-%m-%d') for session in sessions]
        
        if user.role == 'engineer':
            if user.team:
                # Get user's votes over time
                user_votes = {}
                for session in sessions:
                    votes = Vote.objects.filter(user=user, session=session)
                    
                    for card in cards:
                        try:
                            vote = votes.get(card=card)
                            if card.id not in user_votes:
                                user_votes[card.id] = {'green': [], 'amber': [], 'red': []}
                            
                            if vote.value == 'green':
                                user_votes[card.id]['green'].append(1)
                                user_votes[card.id]['amber'].append(0)
                                user_votes[card.id]['red'].append(0)
                            elif vote.value == 'amber':
                                user_votes[card.id]['green'].append(0)
                                user_votes[card.id]['amber'].append(1)
                                user_votes[card.id]['red'].append(0)
                            elif vote.value == 'red':
                                user_votes[card.id]['green'].append(0)
                                user_votes[card.id]['amber'].append(0)
                                user_votes[card.id]['red'].append(1)
                        except Vote.DoesNotExist:
                            if card.id not in user_votes:
                                user_votes[card.id] = {'green': [], 'amber': [], 'red': []}
                            user_votes[card.id]['green'].append(0)
                            user_votes[card.id]['amber'].append(0)
                            user_votes[card.id]['red'].append(0)
                
                # Populate datasets with user votes
                for i, card in enumerate(cards):
                    if card.id in user_votes:
                        datasets[i*3]['data'] = user_votes[card.id]['green']
                        datasets[i*3+1]['data'] = user_votes[card.id]['amber']
                        datasets[i*3+2]['data'] = user_votes[card.id]['red']
                
                context['user_votes'] = user_votes
        
        elif user.role in ['team_leader', 'department_leader', 'senior_manager']:
            # Get team selection
            team_id = request.GET.get('team')
            
            # For team leaders, default to their team if not specified
            if user.role == 'team_leader' and not team_id and user.team:
                team_id = user.team.id
            
            if team_id:
                try:
                    selected_team = Team.objects.get(id=team_id)
                    
                    # Check permission for viewing this team
                    can_view = False
                    if user.role == 'senior_manager':
                        can_view = True
                    elif user.role == 'department_leader' and user.department == selected_team.department:
                        can_view = True
                    elif user.role == 'team_leader' and user.team == selected_team:
                        can_view = True
                    
                    if can_view:
                        # Get team summaries for this team
                        team_data = {'green': {}, 'amber': {}, 'red': {}, 'progress': {}}
                        
                        for session in sessions:
                            summaries = TeamSummary.objects.filter(team=selected_team, session=session)
                            
                            for card in cards:
                                card_key = f"card_{card.id}"
                                if card_key not in team_data['green']:
                                    team_data['green'][card_key] = []
                                    team_data['amber'][card_key] = []
                                    team_data['red'][card_key] = []
                                    team_data['progress'][card_key] = []
                                
                                try:
                                    summary = summaries.get(card=card)
                                    team_data['green'][card_key].append(summary.green_percentage)
                                    team_data['amber'][card_key].append(summary.amber_percentage)
                                    team_data['red'][card_key].append(summary.red_percentage)
                                    team_data['progress'][card_key].append(summary.progress_summary)
                                except TeamSummary.DoesNotExist:
                                    team_data['green'][card_key].append(0)
                                    team_data['amber'][card_key].append(0)
                                    team_data['red'][card_key].append(0)
                                    team_data['progress'][card_key].append('same')
                        
                        # Populate datasets with team data
                        for i, card in enumerate(cards):
                            card_key = f"card_{card.id}"
                            if card_key in team_data['green']:
                                datasets[i*3]['data'] = team_data['green'][card_key]
                                datasets[i*3+1]['data'] = team_data['amber'][card_key]
                                datasets[i*3+2]['data'] = team_data['red'][card_key]
                    
                        context['team_data'] = team_data
                    
                    context['selected_team'] = selected_team
                except Team.DoesNotExist:
                    pass
            
            # Get department selection for department leaders and senior managers
            if user.role in ['department_leader', 'senior_manager']:
                dept_id = request.GET.get('department')
                
                # For department leaders, default to their department if not specified
                if user.role == 'department_leader' and not dept_id and user.department:
                    dept_id = user.department.id
                
                if dept_id:
                    try:
                        selected_department = Department.objects.get(id=dept_id)
                        
                        # Check permission for viewing this department
                        can_view = False
                        if user.role == 'senior_manager':
                            can_view = True
                        elif user.role == 'department_leader' and user.department == selected_department:
                            can_view = True
                        
                        if can_view and not selected_team:
                            # Get department summaries for this department
                            dept_data = {'green': {}, 'amber': {}, 'red': {}, 'progress': {}}
                            
                            for session in sessions:
                                summaries = DepartmentSummary.objects.filter(department=selected_department, session=session)
                                
                                for card in cards:
                                    card_key = f"card_{card.id}"
                                    if card_key not in dept_data['green']:
                                        dept_data['green'][card_key] = []
                                        dept_data['amber'][card_key] = []
                                        dept_data['red'][card_key] = []
                                        dept_data['progress'][card_key] = []
                                    
                                    try:
                                        summary = summaries.get(card=card)
                                        dept_data['green'][card_key].append(summary.green_percentage)
                                        dept_data['amber'][card_key].append(summary.amber_percentage)
                                        dept_data['red'][card_key].append(summary.red_percentage)
                                        dept_data['progress'][card_key].append(summary.progress_summary)
                                    except DepartmentSummary.DoesNotExist:
                                        dept_data['green'][card_key].append(0)
                                        dept_data['amber'][card_key].append(0)
                                        dept_data['red'][card_key].append(0)
                                        dept_data['progress'][card_key].append('same')
                            
                            # Populate datasets with department data
                            if not team_data:  # Only use department data if team data not already used
                                for i, card in enumerate(cards):
                                    card_key = f"card_{card.id}"
                                    if card_key in dept_data['green']:
                                        datasets[i*3]['data'] = dept_data['green'][card_key]
                                        datasets[i*3+1]['data'] = dept_data['amber'][card_key]
                                        datasets[i*3+2]['data'] = dept_data['red'][card_key]
                            
                            context['dept_data'] = dept_data
                        
                        context['selected_department'] = selected_department
                        
                        # Get teams for this department
                        teams = Team.objects.filter(department=selected_department)
                        context['teams'] = teams
                    except Department.DoesNotExist:
                        pass
            
            # For senior managers, get all departments
            if user.role == 'senior_manager':
                departments = Department.objects.all()
                context['departments'] = departments
                
                # If neither team nor department are selected, show organization-wide data
                if not selected_team and not selected_department:
                    org_data = {'green': {}, 'amber': {}, 'red': {}, 'progress': {}}
                    
                    for session in sessions:
                        # Aggregate department summaries for each card
                        for card in cards:
                            card_key = f"card_{card.id}"
                            if card_key not in org_data['green']:
                                org_data['green'][card_key] = []
                                org_data['amber'][card_key] = []
                                org_data['red'][card_key] = []
                                org_data['progress'][card_key] = []
                            
                            dept_summaries = DepartmentSummary.objects.filter(session=session, card=card)
                            
                            if dept_summaries.exists():
                                green_avg = dept_summaries.aggregate(avg=Avg('green_percentage'))['avg'] or 0
                                amber_avg = dept_summaries.aggregate(avg=Avg('amber_percentage'))['avg'] or 0
                                red_avg = dept_summaries.aggregate(avg=Avg('red_percentage'))['avg'] or 0
                                
                                org_data['green'][card_key].append(green_avg)
                                org_data['amber'][card_key].append(amber_avg)
                                org_data['red'][card_key].append(red_avg)
                                
                                # Determine most common progress
                                progress_counts = {
                                    'better': dept_summaries.filter(progress_summary='better').count(),
                                    'same': dept_summaries.filter(progress_summary='same').count(),
                                    'worse': dept_summaries.filter(progress_summary='worse').count()
                                }
                                
                                if progress_counts['better'] >= progress_counts['same'] and progress_counts['better'] >= progress_counts['worse']:
                                    org_data['progress'][card_key].append('better')
                                elif progress_counts['same'] >= progress_counts['better'] and progress_counts['same'] >= progress_counts['worse']:
                                    org_data['progress'][card_key].append('same')
                                else:
                                    org_data['progress'][card_key].append('worse')
                            else:
                                org_data['green'][card_key].append(0)
                                org_data['amber'][card_key].append(0)
                                org_data['red'][card_key].append(0)
                                org_data['progress'][card_key].append('same')
                    
                    # Populate datasets with organization data
                    for i, card in enumerate(cards):
                        card_key = f"card_{card.id}"
                        if card_key in org_data['green']:
                            datasets[i*3]['data'] = org_data['green'][card_key]
                            datasets[i*3+1]['data'] = org_data['amber'][card_key]
                            datasets[i*3+2]['data'] = org_data['red'][card_key]
                    
                    context['org_data'] = org_data
    
    # Calculate status distribution data for pie chart
    status_data = {'green': 0, 'amber': 0, 'red': 0}
    
    if team_data:
        # Use the most recent session data for the selected team
        for card in cards:
            card_key = f"card_{card.id}"
            if card_key in team_data['green'] and team_data['green'][card_key]:
                status_data['green'] += team_data['green'][card_key][-1]
                status_data['amber'] += team_data['amber'][card_key][-1]
                status_data['red'] += team_data['red'][card_key][-1]
    elif dept_data:
        # Use the most recent session data for the selected department
        for card in cards:
            card_key = f"card_{card.id}"
            if card_key in dept_data['green'] and dept_data['green'][card_key]:
                status_data['green'] += dept_data['green'][card_key][-1]
                status_data['amber'] += dept_data['amber'][card_key][-1]
                status_data['red'] += dept_data['red'][card_key][-1]
    elif 'org_data' in context:
        # Use the most recent session data for the organization
        for card in cards:
            card_key = f"card_{card.id}"
            if card_key in context['org_data']['green'] and context['org_data']['green'][card_key]:
                status_data['green'] += context['org_data']['green'][card_key][-1]
                status_data['amber'] += context['org_data']['amber'][card_key][-1]
                status_data['red'] += context['org_data']['red'][card_key][-1]
    
    # Normalize status data
    status_total = status_data['green'] + status_data['amber'] + status_data['red']
    if status_total > 0:
        status_data = {
            'green': round(status_data['green'] / len(cards), 1) if len(cards) > 0 else 0,
            'amber': round(status_data['amber'] / len(cards), 1) if len(cards) > 0 else 0,
            'red': round(status_data['red'] / len(cards), 1) if len(cards) > 0 else 0
        }
    
    # Calculate progress distribution data for pie chart
    progress_counts = {'better': 0, 'same': 0, 'worse': 0}
    
    if team_data and 'progress' in team_data:
        # Count progress from the most recent session for each card
        for card in cards:
            card_key = f"card_{card.id}"
            if card_key in team_data['progress'] and team_data['progress'][card_key]:
                last_progress = team_data['progress'][card_key][-1]
                progress_counts[last_progress] += 1
    elif dept_data and 'progress' in dept_data:
        # Count progress from the most recent session for each card
        for card in cards:
            card_key = f"card_{card.id}"
            if card_key in dept_data['progress'] and dept_data['progress'][card_key]:
                last_progress = dept_data['progress'][card_key][-1]
                progress_counts[last_progress] += 1
    elif 'org_data' in context and 'progress' in context['org_data']:
        # Count progress from the most recent session for each card
        for card in cards:
            card_key = f"card_{card.id}"
            if card_key in context['org_data']['progress'] and context['org_data']['progress'][card_key]:
                last_progress = context['org_data']['progress'][card_key][-1]
                progress_counts[last_progress] += 1
    
    # Prepare chart data for JS
    chart_data = {
        'labels': session_dates,
        'datasets': datasets
    }
    
    # Add chart data and distribution data to context
    context['chart_data'] = json.dumps(chart_data)
    context['status_data'] = status_data
    context['progress_counts'] = progress_counts
    
    return render(request, 'core/progress_chart.html', context)

def update_team_summary(team, session, card):
    """
    Update team summary for a card and session based on team members' votes.
    
    This function aggregates individual team member votes into team-level metrics,
    calculating percentages for each vote value (green/amber/red) and determining
    the overall team status and progress trend. It's called after each vote to
    ensure team summaries are always current.
    
    Data Integrity:
        - Uses database transaction to ensure atomic updates
        - Handles edge cases like empty vote sets
        - Implements majority-wins logic for determining overall status
    
    Performance Optimization:
        - Uses Django's annotate and values for efficient vote counting
        - Uses update_or_create to minimize database operations
        - Triggers department summary updates only when necessary
    
    Args:
        team: Team object whose summary is being updated
        session: Session object representing the time period
        card: HealthCheckCard object representing the category
        
    Database:
        - Reads from Vote model to get team members' votes
        - Creates or updates TeamSummary record
        - May trigger DepartmentSummary updates
    """
    # Use transaction.atomic to ensure data consistency
    # This prevents partial updates if an error occurs mid-process
    with transaction.atomic():
        # Get all votes for this team, session, and card combination
        # This query finds all votes from users belonging to the specified team
        votes = Vote.objects.filter(
            user__team=team,  # Filter by team membership via user relationship
            session=session,  # Filter by specific session
            card=card         # Filter by specific health check card
        )
        
        # Only proceed if votes exist for this combination
        if votes.exists():
            # Count votes by value (green/amber/red) using efficient aggregation
            # This produces a queryset of dictionaries with value and count pairs
            vote_counts = votes.values('value').annotate(count=Count('value'))
            # Convert to a more convenient dictionary format for easier access
            vote_count_dict = {vc['value']: vc['count'] for vc in vote_counts}
            
            # Calculate percentages for each vote value
            # These percentages show the distribution of team sentiment
            total_votes = votes.count()
            # Handle division by zero with conditional logic
            green_pct = (vote_count_dict.get('green', 0) / total_votes) * 100 if total_votes > 0 else 0
            amber_pct = (vote_count_dict.get('amber', 0) / total_votes) * 100 if total_votes > 0 else 0
            red_pct = (vote_count_dict.get('red', 0) / total_votes) * 100 if total_votes > 0 else 0
            
            # Determine average vote using majority-wins logic
            # This represents the team's overall status for this card
            if green_pct >= amber_pct and green_pct >= red_pct:
                avg_vote = 'green'  # Green has highest percentage
            elif amber_pct >= green_pct and amber_pct >= red_pct:
                avg_vote = 'amber'  # Amber has highest percentage
            else:
                avg_vote = 'red'    # Red has highest percentage
            
            # Count progress notes (better/same/worse) using efficient aggregation
            # This shows the team's perception of trend direction
            progress_counts = votes.values('progress_note').annotate(count=Count('progress_note'))
            progress_count_dict = {pc['progress_note']: pc['count'] for pc in progress_counts}
            
            # Determine progress summary using majority-wins logic
            # This represents the team's overall trend perception
            better_count = progress_count_dict.get('better', 0)
            same_count = progress_count_dict.get('same', 0)
            worse_count = progress_count_dict.get('worse', 0)
            
            if better_count >= same_count and better_count >= worse_count:
                progress_summary = 'better'  # Most votes indicate improvement
            elif same_count >= better_count and same_count >= worse_count:
                progress_summary = 'same'    # Most votes indicate stability
            else:
                progress_summary = 'worse'   # Most votes indicate decline
            
            # Update or create team summary record with calculated metrics
            # This efficiently handles both new and existing summaries
            TeamSummary.objects.update_or_create(
                # Lookup parameters to find existing record
                team=team,
                session=session,
                card=card,
                # Values to update or set if creating new record
                defaults={
                    'average_vote': avg_vote,           # Overall team status
                    'progress_summary': progress_summary, # Overall trend direction
                    'green_percentage': green_pct,      # Percentage of green votes
                    'amber_percentage': amber_pct,      # Percentage of amber votes
                    'red_percentage': red_pct,          # Percentage of red votes
                }
            )
            
            # Now update department summary if this team belongs to a department
            # This ensures department-level aggregations stay current
            if team.department:
                update_department_summary(team.department, session, card)

def update_department_summary(department, session, card):
    """
    Update department summary based on team summaries.
    
    This function aggregates team-level summaries into department-level metrics,
    calculating average percentages for each vote value (green/amber/red) and 
    determining the overall department status and progress trend. It's called
    after team summaries are updated to ensure department data stays current.
    
    Data Integrity:
        - Uses database transaction to ensure atomic updates
        - Handles edge cases like empty team summary sets
        - Implements majority-wins logic for determining overall status
    
    Performance Optimization:
        - Uses Django's aggregate for efficient average calculations
        - Uses filter and count for progress summary determination
        - Uses update_or_create to minimize database operations
    
    Args:
        department: Department object whose summary is being updated
        session: Session object representing the time period
        card: HealthCheckCard object representing the category
        
    Database:
        - Reads from TeamSummary model to get team-level metrics
        - Creates or updates DepartmentSummary record
    """
    # Use transaction.atomic to ensure data consistency
    # This prevents partial updates if an error occurs mid-process
    with transaction.atomic():
        # Get all team summaries for this department, session, and card combination
        # This finds all team summaries for teams belonging to the specified department
        team_summaries = TeamSummary.objects.filter(
            team__department=department,  # Filter by department via team relationship
            session=session,              # Filter by specific session
            card=card                     # Filter by specific health check card
        )
        
        # Only proceed if team summaries exist for this combination
        if team_summaries.exists():
            # Calculate average percentages across all teams in the department
            # This provides department-wide metrics based on team averages
            green_pct = team_summaries.aggregate(avg=Avg('green_percentage'))['avg']
            amber_pct = team_summaries.aggregate(avg=Avg('amber_percentage'))['avg']
            red_pct = team_summaries.aggregate(avg=Avg('red_percentage'))['avg']
            
            # Determine average vote using highest-percentage logic
            # This represents the department's overall status for this card
            if green_pct >= amber_pct and green_pct >= red_pct:
                avg_vote = 'green'  # Green has highest percentage
            elif amber_pct >= green_pct and amber_pct >= red_pct:
                avg_vote = 'amber'  # Amber has highest percentage
            else:
                avg_vote = 'red'    # Red has highest percentage
            
            # Count team progress summaries to determine department trend
            # This shows how many teams are improving, stable, or declining
            progress_counts = {
                'better': team_summaries.filter(progress_summary='better').count(),
                'same': team_summaries.filter(progress_summary='same').count(),
                'worse': team_summaries.filter(progress_summary='worse').count()
            }
            
            # Determine department progress summary using majority-wins logic
            # This represents the department's overall trend direction
            if progress_counts['better'] >= progress_counts['same'] and progress_counts['better'] >= progress_counts['worse']:
                progress_summary = 'better'  # Most teams are improving
            elif progress_counts['same'] >= progress_counts['better'] and progress_counts['same'] >= progress_counts['worse']:
                progress_summary = 'same'    # Most teams are stable
            else:
                progress_summary = 'worse'   # Most teams are declining
            
            # Update or create department summary record with calculated metrics
            # This efficiently handles both new and existing summaries
            DepartmentSummary.objects.update_or_create(
                # Lookup parameters to find existing record
                department=department,
                session=session,
                card=card,
                # Values to update or set if creating new record
                defaults={
                    'average_vote': avg_vote,           # Overall department status
                    'progress_summary': progress_summary, # Overall trend direction
                    'green_percentage': green_pct,      # Average percentage of green votes
                    'amber_percentage': amber_pct,      # Average percentage of amber votes
                    'red_percentage': red_pct,          # Average percentage of red votes
                }
            )

def load_teams(request):
    """
    AJAX endpoint to load teams belonging to a specific department.
    
    This view handles asynchronous requests to fetch teams within a selected
    department. It's primarily used for dynamic form population, allowing
    department selection to filter available teams in dependent dropdowns.
    
    Args:
        request: HttpRequest object containing metadata about the request
        
    Returns:
        JsonResponse: JSON array of team objects with id and name properties
        
    Query Parameters:
        department: ID of the department to filter teams by
        
    Database:
        - Reads from Team model filtered by department_id
        - Optimizes query with ordering by name for consistent display
    """
    # Get department_id from query parameters
    department_id = request.GET.get('department')
    
    # Query teams belonging to the specified department, ordered alphabetically
    teams = Team.objects.filter(department_id=department_id).order_by('name')
    
    # Return JSON array of team objects with minimal properties needed for dropdown
    # The safe=False parameter allows returning a non-dict object as JSON
    return JsonResponse([{'id': team.id, 'name': team.name} for team in teams], safe=False)

@login_required
def team_detail_view(request, team_id):
    """
    Display detailed information for a specific team.
    
    This view provides comprehensive information about a team, including its
    members, recent health check summaries, and participation statistics.
    It's used by team leaders to monitor their team and by department leaders
    and senior managers to review individual team performance.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Enforces team access permissions based on user role
        - Engineers can only view their own team's details
    
    Args:
        request: HttpRequest object containing metadata about the request
        team_id: ID of the team to view details for
        
    Returns:
        HttpResponse: Renders the team detail view with context data
        HttpResponseForbidden: If user lacks permission to view the team
        
    Template:
        core/team_detail.html - Receives team details context
        
    Database:
        - Reads from Team, User, Session, Vote, and TeamSummary models
        - Uses select_related for optimized queries
        - Limits recent summaries to 10 for performance
    """
    user = request.user
    # Get team or return 404 if not found
    team = get_object_or_404(Team, id=team_id)
    
    # Check permissions - engineers can only view their own team
    # This enforces role-based access control at the view level
    if user.role == 'engineer' and user.team != team:
        return HttpResponseForbidden('You do not have permission to view this team.')
    
    # Get team members for display and participation tracking
    # This shows who belongs to the team and their voting status
    members = User.objects.filter(team=team)
    
    # Get latest session for participation tracking
    # This assumes sessions are ordered by recency (newest first)
    latest_session = Session.objects.first()
    
    # Flag if each member has voted in latest session
    # This helps identify team members who haven't participated
    for member in members:
        # Check if the member has any votes in the latest session
        # The conditional handles the case where no sessions exist
        member.has_voted_in_session = Vote.objects.filter(user=member, session=latest_session).exists() if latest_session else False
    
    # Get recent team summaries for health trend analysis
    # Using select_related optimizes the query by fetching related objects
    # Limiting to 10 recent summaries balances detail with performance
    summaries = TeamSummary.objects.filter(team=team).select_related('card', 'session').order_by('-session__date')[:10]
    
    # Render the team detail template with comprehensive context
    return render(request, 'core/team_detail.html', {
        'team': team,           # The team being viewed
        'members': members,     # Team members with participation flags
        'summaries': summaries, # Recent health check summaries
    })

@login_required
def department_detail_view(request, department_id):
    """
    Display detailed information for a specific department.
    
    This view provides comprehensive information about a department, including its
    leadership, teams, and recent health check summaries. It's used by department
    leaders to monitor their department and by senior managers to review
    individual department performance.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Enforces department access permissions using the User model's permission method
        - Uses a custom permission check method (can_view_department_summary)
    
    Args:
        request: HttpRequest object containing metadata about the request
        department_id: ID of the department to view details for
        
    Returns:
        HttpResponse: Renders the department detail view with context data
        HttpResponseForbidden: If user lacks permission to view the department
        
    Template:
        core/department_detail.html - Receives department details context
        
    Database:
        - Reads from Department, User, Team, and DepartmentSummary models
        - Uses select_related for optimized queries
        - Limits recent summaries to 10 for performance
    """
    user = request.user
    # Get department or return 404 if not found
    department = get_object_or_404(Department, id=department_id)
    
    # Check permissions using the User model's custom permission method
    # This centralizes permission logic in the User model for consistency
    if not user.can_view_department_summary(department):
        return HttpResponseForbidden('You do not have permission to view this department.')
    
    # Get department leaders for display and contact information
    # This shows who is responsible for the department
    leaders = User.objects.filter(department=department, role='department_leader')
    
    # Get teams in this department for organizational structure
    # This shows all teams that make up the department
    teams = Team.objects.filter(department=department)
    
    # Get recent department summaries for health trend analysis
    # Using select_related optimizes the query by fetching related objects
    # Limiting to 10 recent summaries balances detail with performance
    summaries = DepartmentSummary.objects.filter(
        department=department
    ).select_related('card', 'session').order_by('-session__date')[:10]
    
    # Render the department detail template with comprehensive context
    return render(request, 'core/department_detail.html', {
        'department': department,  # The department being viewed
        'leaders': leaders,        # Department leadership
        'teams': teams,            # Teams within the department
        'summaries': summaries,    # Recent health check summaries
    })

@login_required
def health_status_dashboard(request):
    """
    Display a comprehensive health status dashboard for leadership roles.
    
    This view provides a high-level overview of the organization's health check status,
    highlighting teams at risk, trend directions, and key metrics. It serves as
    a central monitoring tool for team leaders, department leaders, and senior managers
    to quickly identify areas requiring attention.
    
    Security:
        - Requires user authentication (@login_required decorator)
        - Restricts access to leadership roles (team leader and above)
        - Provides role-appropriate organizational visibility
    
    Args:
        request: HttpRequest object containing metadata about the request
        
    Returns:
        HttpResponse: Renders the health status dashboard with context data
        HttpResponseRedirect: Redirects to main dashboard if permission denied
        
    Template:
        core/health_status.html - Receives comprehensive health status context
        
    Database:
        - Reads from multiple models including Team, Department, User, Session, TeamSummary, and Vote
        - Performs complex calculations and aggregations for status metrics
        - Uses select_related for optimized queries where appropriate
    """
    user = request.user
    
    # This view is only for team leaders and above - enforce role-based access control
    if user.role not in ['team_leader', 'department_leader', 'senior_manager', 'admin']:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    # Get organization-wide counts for high-level metrics
    # These provide context on the size and structure of the organization
    team_count = Team.objects.count()
    department_count = Department.objects.count()
    user_count = User.objects.count()
    
    # Get active session for current health check period
    # This ensures we're analyzing the most recent data
    active_session = Session.objects.filter(is_active=True).first()
    
    # Get teams by health status to identify distribution and at-risk teams
    # This is core functionality for the dashboard - identifying problem areas
    teams = Team.objects.all()
    green_teams = 0  # Teams with good health status
    amber_teams = 0  # Teams with warning health status
    red_teams = 0    # Teams with critical health status
    teams_at_risk = []  # Collection of amber and red teams for focused attention
    
    # Analyze each team's health status and categorize accordingly
    for team in teams:
        # Get the team's latest overall health status (from Team model method)
        status = team.get_latest_health_status()
        
        if status == 'green':
            # Team is healthy - increment green count
            green_teams += 1
            
        elif status == 'amber':
            # Team has warning signs - increment amber count and add to at-risk list
            amber_teams += 1
            
            # Add team to at-risk list with status for UI highlighting
            team.health_status = 'amber'
            
            # Find the most critical health check card for this team
            # This helps identify the specific area causing the warning status
            if active_session:
                # Get the summary with lowest green percentage (most concerning)
                critical_summary = TeamSummary.objects.filter(
                    team=team, 
                    session=active_session
                ).order_by('green_percentage').first()  # Ascending order - lowest first
                
                # Store critical card name on team object for display
                team.critical_card = critical_summary.card.name if critical_summary else 'Unknown'
                teams_at_risk.append(team)
                
        elif status == 'red':
            # Team is in critical condition - increment red count and add to at-risk list
            red_teams += 1
            
            # Add team to at-risk list with status for UI highlighting
            team.health_status = 'red'
            
            # Find the most critical health check card for this team
            # For red teams, we specifically look for cards with red average vote
            if active_session:
                critical_summary = TeamSummary.objects.filter(
                    team=team, 
                    session=active_session, 
                    average_vote='red'  # Only consider cards with red status
                ).first()
                
                # Store critical card name on team object for display
                team.critical_card = critical_summary.card.name if critical_summary else 'Unknown'
                teams_at_risk.append(team)
    
    # Count trend directions to show overall organizational movement
    # This helps identify if the organization is generally improving or declining
    improving_count = 0  # Count of improving metrics
    stable_count = 0     # Count of stable metrics
    declining_count = 0  # Count of declining metrics
    
    # Analyze all team summaries to determine trend distributions
    team_summaries = TeamSummary.objects.all()
    for summary in team_summaries:
        # Calculate trend direction using TeamSummary model method
        trend = summary.calculate_trend()
        if trend == 'improving':
            improving_count += 1
        elif trend == 'stable':
            stable_count += 1
        elif trend == 'declining':
            declining_count += 1
    
    # Get recent votes for activity monitoring
    # This shows recent participation and engagement with the health check system
    recent_votes = Vote.objects.select_related('user', 'card').order_by('-created_at')[:5]
    
    # Render the health status dashboard with comprehensive context
    return render(request, 'core/health_status.html', {
        'team_count': team_count,               # Total number of teams
        'department_count': department_count,   # Total number of departments
        'user_count': user_count,               # Total number of users
        'active_session': active_session,       # Current active session
        'green_teams': green_teams,             # Count of healthy teams
        'amber_teams': amber_teams,             # Count of warning status teams
        'red_teams': red_teams,                 # Count of critical status teams
        'teams_at_risk': teams_at_risk,         # List of teams needing attention
        'improving_count': improving_count,     # Count of improving metrics
        'stable_count': stable_count,           # Count of stable metrics
        'declining_count': declining_count,     # Count of declining metrics
        'recent_votes': recent_votes,           # Recent system activity
    })

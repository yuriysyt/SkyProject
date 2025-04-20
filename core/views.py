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
    user = request.user
    today = timezone.now().date()
    
    # Get active sessions
    active_sessions = Session.objects.filter(is_active=True)
    
    # Initialize context with common data
    context = {
        'user': user,
        'active_sessions': active_sessions,
        'today': today,
    }
    
    # Load role-specific data
    if user.role == 'engineer':
        # Get user's team
        if user.team:
            # Get all health check cards
            cards = HealthCheckCard.objects.filter(active=True)
            
            # Get latest session
            latest_session = Session.objects.first()
            
            # Get user's votes for latest session
            user_votes = {}
            if latest_session:
                votes = Vote.objects.filter(
                    user=user,
                    session=latest_session
                )
                user_votes = {vote.card_id: vote for vote in votes}
                
            # Team summaries for user's team
            team_summaries = TeamSummary.objects.filter(team=user.team)
            
            context.update({
                'cards': cards,
                'latest_session': latest_session,
                'user_votes': user_votes,
                'team_summaries': team_summaries,
            })
    
    elif user.role == 'team_leader':
        # Get team leader's team and department
        team = user.team
        department = user.department
        
        if team:
            # Get team members
            team_members = User.objects.filter(team=team)
            
            # Get team summaries
            team_summaries = TeamSummary.objects.filter(team=team)
            
            # Get health check cards
            cards = HealthCheckCard.objects.filter(active=True)
            
            # Get latest session
            latest_session = Session.objects.first()
            
            # Get team leader's votes
            user_votes = {}
            if latest_session:
                votes = Vote.objects.filter(
                    user=user,
                    session=latest_session
                )
                user_votes = {vote.card_id: vote for vote in votes}
            
            # Get other teams in the department
            other_teams = Team.objects.filter(department=department).exclude(id=team.id)
            
            context.update({
                'team': team,
                'team_members': team_members,
                'team_summaries': team_summaries,
                'other_teams': other_teams,
                'cards': cards,
                'latest_session': latest_session,
                'user_votes': user_votes,
            })
        
    elif user.role == 'department_leader':
        # Get department
        department = user.department
        
        if department:
            # Get teams in department
            teams = Team.objects.filter(department=department)
            
            # Get department summaries
            department_summaries = DepartmentSummary.objects.filter(department=department)
            
            # Get team summaries for all teams in department
            team_summaries = TeamSummary.objects.filter(team__department=department)
            
            # Get other departments
            other_departments = Department.objects.exclude(id=department.id)
            
            context.update({
                'department': department,
                'teams': teams,
                'department_summaries': department_summaries,
                'team_summaries': team_summaries,
                'other_departments': other_departments,
            })
        
    elif user.role == 'senior_manager':
        # Get all departments
        departments = Department.objects.all()
        
        # Get all team summaries
        team_summaries = TeamSummary.objects.all()
        
        # Get all department summaries
        department_summaries = DepartmentSummary.objects.all()
        
        context.update({
            'departments': departments,
            'team_summaries': team_summaries,
            'department_summaries': department_summaries,
        })
    
    return render(request, 'core/dashboard.html', context)

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'core/profile.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'core/change_password.html', {'form': form})

@login_required
def vote(request, session_id, card_id):
    # Get session and card
    session = get_object_or_404(Session, id=session_id)
    card = get_object_or_404(HealthCheckCard, id=card_id)
    
    # Check if user is engineer or team leader
    if request.user.role not in ['engineer', 'team_leader']:
        messages.error(request, 'Only engineers and team leaders can vote.')
        return redirect('dashboard')
    
    # Check if user has a team
    if not request.user.team:
        messages.error(request, 'You must be assigned to a team to vote.')
        return redirect('dashboard')
    
    # Check if session is active
    if not session.is_active:
        messages.error(request, 'This session is no longer active.')
        return redirect('dashboard')
    
    # Get existing vote or create new one
    try:
        vote = Vote.objects.get(user=request.user, session=session, card=card)
    except Vote.DoesNotExist:
        vote = None
    
    if request.method == 'POST':
        form = VoteForm(request.POST, instance=vote)
        if form.is_valid():
            vote = form.save(commit=False)
            vote.user = request.user
            vote.session = session
            vote.card = card
            vote.save()
            
            # Update team summary
            update_team_summary(request.user.team, session, card)
            
            messages.success(request, 'Vote submitted successfully!')
            return redirect('dashboard')
    else:
        form = VoteForm(instance=vote)
    
    return render(request, 'core/vote.html', {
        'form': form,
        'session': session,
        'card': card,
        'vote': vote
    })

@login_required
def vote_all(request, session_id):
    """View for voting on all cards at once."""
    # Get session
    session = get_object_or_404(Session, id=session_id)
    
    # Check if user is engineer or team leader
    if request.user.role not in ['engineer', 'team_leader']:
        messages.error(request, 'Only engineers and team leaders can vote.')
        return redirect('dashboard')
    
    # Check if user has a team
    if not request.user.team:
        messages.error(request, 'You must be assigned to a team to vote.')
        return redirect('dashboard')
    
    # Check if session is active
    if not session.is_active:
        messages.error(request, 'This session is no longer active.')
        return redirect('dashboard')
    
    # Get all active health check cards
    cards = HealthCheckCard.objects.filter(active=True).order_by('order')
    
    # Get user's existing votes for this session
    user_votes = {}
    votes = Vote.objects.filter(user=request.user, session=session)
    for vote in votes:
        user_votes[vote.card_id] = vote
    
    return render(request, 'core/vote_all.html', {
        'session': session,
        'cards': cards,
        'user_votes': user_votes
    })

@login_required
def vote_all_submit(request, session_id):
    """Handle submission of votes for all cards."""
    if request.method != 'POST':
        return redirect('dashboard')
    
    # Get session
    session = get_object_or_404(Session, id=session_id)
    
    # Check permissions
    if request.user.role not in ['engineer', 'team_leader']:
        messages.error(request, 'Only engineers and team leaders can vote.')
        return redirect('dashboard')
    
    if not request.user.team:
        messages.error(request, 'You must be assigned to a team to vote.')
        return redirect('dashboard')
    
    if not session.is_active:
        messages.error(request, 'This session is no longer active.')
        return redirect('dashboard')
    
    # Get card IDs from the form
    card_ids = request.POST.getlist('card_ids')
    
    # Process each card's vote
    success_count = 0
    error_count = 0
    
    with transaction.atomic():
        for card_id in card_ids:
            card_id = int(card_id)
            card = get_object_or_404(HealthCheckCard, id=card_id)
            
            # Get form values for this card
            value = request.POST.get(f'value_{card_id}')
            progress_note = request.POST.get(f'progress_{card_id}')
            comment = request.POST.get(f'comment_{card_id}', '')
            
            if not value or not progress_note:
                error_count += 1
                continue
            
            # Get or create vote
            try:
                vote = Vote.objects.get(user=request.user, session=session, card=card)
            except Vote.DoesNotExist:
                vote = Vote(user=request.user, session=session, card=card)
            
            # Update vote
            vote.value = value
            vote.progress_note = progress_note
            vote.comment = comment
            vote.save()
            
            # Update team summary
            update_team_summary(request.user.team, session, card)
            
            success_count += 1
    
    if success_count > 0:
        messages.success(request, f'Successfully submitted {success_count} votes.')
    
    if error_count > 0:
        messages.warning(request, f'Failed to submit {error_count} votes due to missing required fields.')
    
    return redirect('dashboard')

@login_required
def team_summary(request, team_id=None):
    user = request.user
    
    # Check permissions
    if user.role not in ['team_leader', 'department_leader', 'senior_manager']:
        messages.error(request, 'You do not have permission to view team summaries.')
        return redirect('dashboard')
    
    # Get team (either specified or user's team)
    if team_id:
        team = get_object_or_404(Team, id=team_id)
        
        # Check if user has permission to view this team
        if user.role == 'team_leader' and team != user.team:
            if team.department != user.department:
                return HttpResponseForbidden('You do not have permission to view this team.')
    else:
        team = user.team
    
    # Get session selection form
    session_form = SessionSelectionForm(request.GET or None)
    selected_session = None
    
    if session_form.is_valid():
        selected_session = session_form.cleaned_data['session']
    else:
        # Default to latest session
        selected_session = Session.objects.first()
    
    if team and selected_session:
        # Get team summaries for selected session
        summaries = TeamSummary.objects.filter(team=team, session=selected_session)
        
        # Get team members
        team_members = User.objects.filter(team=team)
        
        # Get health check cards
        cards = HealthCheckCard.objects.filter(active=True)
        
        return render(request, 'core/team_summary.html', {
            'team': team,
            'session': selected_session,
            'summaries': summaries,
            'team_members': team_members,
            'cards': cards,
            'session_form': session_form,
        })
    
    messages.error(request, 'Please select a team and session.')
    return redirect('dashboard')

@login_required
def department_summary(request, department_id=None):
    user = request.user
    
    # Check permissions
    if user.role not in ['department_leader', 'senior_manager']:
        messages.error(request, 'You do not have permission to view department summaries.')
        return redirect('dashboard')
    
    # Get department (either specified or user's department)
    if department_id:
        department = get_object_or_404(Department, id=department_id)
        
        # Check if user has permission to view this department
        if user.role == 'department_leader' and department != user.department:
            return HttpResponseForbidden('You do not have permission to view this department.')
    else:
        department = user.department
    
    # Get session selection form
    session_form = SessionSelectionForm(request.GET or None)
    selected_session = None
    
    if session_form.is_valid():
        selected_session = session_form.cleaned_data['session']
    else:
        # Default to latest session
        selected_session = Session.objects.first()
    
    if department and selected_session:
        # Get department summaries for selected session
        dept_summaries = DepartmentSummary.objects.filter(
            department=department, 
            session=selected_session
        )
        
        # Get teams in department
        teams = Team.objects.filter(department=department)
        
        # Get team summaries for all teams in the department
        team_summaries = TeamSummary.objects.filter(
            team__in=teams,
            session=selected_session
        )
        
        # Get health check cards
        cards = HealthCheckCard.objects.filter(active=True)
        
        return render(request, 'core/department_summary.html', {
            'department': department,
            'session': selected_session,
            'dept_summaries': dept_summaries,
            'teams': teams,
            'team_summaries': team_summaries,
            'cards': cards,
            'session_form': session_form,
        })
    
    messages.error(request, 'Please select a department and session.')
    return redirect('dashboard')

@login_required
def progress_chart(request):
    user = request.user
    
    # Get date range selection
    date_form = DateRangeForm(request.GET or None)
    
    if date_form.is_valid():
        start_date = date_form.cleaned_data['start_date']
        end_date = date_form.cleaned_data['end_date']
    else:
        # Default to last 6 months
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=180)
    
    # Get sessions in date range
    sessions = Session.objects.filter(date__range=[start_date, end_date]).order_by('date')
    
    # Get chart data
    chart_data = {}
    session_dates = []
    team_data = None
    selected_team = None
    dept_data = None
    selected_department = None
    
    # Initialize context
    context = {
        'date_form': date_form,
        'start_date': start_date,
        'end_date': end_date,
        'sessions': sessions,
    }
    
    # Get all health check cards for labels
    cards = HealthCheckCard.objects.filter(active=True).order_by('order')
    card_names = [card.name for card in cards]
    
    # Create empty datasets structure for chart
    datasets = []
    for card in cards:
        green_dataset = {
            'label': f'{card.name} - Green',
            'data': [],
            'backgroundColor': 'rgba(34, 197, 94, 0.2)',
            'borderColor': 'rgba(34, 197, 94, 1)',
            'borderWidth': 2,
            'tension': 0.3
        }
        amber_dataset = {
            'label': f'{card.name} - Amber',
            'data': [],
            'backgroundColor': 'rgba(245, 158, 11, 0.2)',
            'borderColor': 'rgba(245, 158, 11, 1)',
            'borderWidth': 2,
            'tension': 0.3
        }
        red_dataset = {
            'label': f'{card.name} - Red',
            'data': [],
            'backgroundColor': 'rgba(239, 68, 68, 0.2)',
            'borderColor': 'rgba(239, 68, 68, 1)',
            'borderWidth': 2,
            'tension': 0.3
        }
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
    This should ideally be a background task or signal handler.
    """
    with transaction.atomic():
        # Get all votes for this team, session, and card
        votes = Vote.objects.filter(
            user__team=team,
            session=session,
            card=card
        )
        
        if votes.exists():
            # Count votes by value
            vote_counts = votes.values('value').annotate(count=Count('value'))
            vote_count_dict = {vc['value']: vc['count'] for vc in vote_counts}
            
            # Calculate percentages
            total_votes = votes.count()
            green_pct = (vote_count_dict.get('green', 0) / total_votes) * 100 if total_votes > 0 else 0
            amber_pct = (vote_count_dict.get('amber', 0) / total_votes) * 100 if total_votes > 0 else 0
            red_pct = (vote_count_dict.get('red', 0) / total_votes) * 100 if total_votes > 0 else 0
            
            # Determine average vote (majority wins)
            if green_pct >= amber_pct and green_pct >= red_pct:
                avg_vote = 'green'
            elif amber_pct >= green_pct and amber_pct >= red_pct:
                avg_vote = 'amber'
            else:
                avg_vote = 'red'
            
            # Count progress notes
            progress_counts = votes.values('progress_note').annotate(count=Count('progress_note'))
            progress_count_dict = {pc['progress_note']: pc['count'] for pc in progress_counts}
            
            # Determine progress summary (majority wins)
            better_count = progress_count_dict.get('better', 0)
            same_count = progress_count_dict.get('same', 0)
            worse_count = progress_count_dict.get('worse', 0)
            
            if better_count >= same_count and better_count >= worse_count:
                progress_summary = 'better'
            elif same_count >= better_count and same_count >= worse_count:
                progress_summary = 'same'
            else:
                progress_summary = 'worse'
            
            # Update or create team summary
            TeamSummary.objects.update_or_create(
                team=team,
                session=session,
                card=card,
                defaults={
                    'average_vote': avg_vote,
                    'progress_summary': progress_summary,
                    'green_percentage': green_pct,
                    'amber_percentage': amber_pct,
                    'red_percentage': red_pct,
                }
            )
            
            # Now update department summary
            if team.department:
                update_department_summary(team.department, session, card)

def update_department_summary(department, session, card):
    """
    Update department summary based on team summaries.
    This should ideally be a background task or signal handler.
    """
    with transaction.atomic():
        # Get all team summaries for this department, session, and card
        team_summaries = TeamSummary.objects.filter(
            team__department=department,
            session=session,
            card=card
        )
        
        if team_summaries.exists():
            # Calculate average percentages
            green_pct = team_summaries.aggregate(avg=Avg('green_percentage'))['avg']
            amber_pct = team_summaries.aggregate(avg=Avg('amber_percentage'))['avg']
            red_pct = team_summaries.aggregate(avg=Avg('red_percentage'))['avg']
            
            # Determine average vote (highest percentage wins)
            if green_pct >= amber_pct and green_pct >= red_pct:
                avg_vote = 'green'
            elif amber_pct >= green_pct and amber_pct >= red_pct:
                avg_vote = 'amber'
            else:
                avg_vote = 'red'
            
            # Count progress summaries
            progress_counts = {
                'better': team_summaries.filter(progress_summary='better').count(),
                'same': team_summaries.filter(progress_summary='same').count(),
                'worse': team_summaries.filter(progress_summary='worse').count()
            }
            
            # Determine progress summary (majority wins)
            if progress_counts['better'] >= progress_counts['same'] and progress_counts['better'] >= progress_counts['worse']:
                progress_summary = 'better'
            elif progress_counts['same'] >= progress_counts['better'] and progress_counts['same'] >= progress_counts['worse']:
                progress_summary = 'same'
            else:
                progress_summary = 'worse'
            
            # Update or create department summary
            DepartmentSummary.objects.update_or_create(
                department=department,
                session=session,
                card=card,
                defaults={
                    'average_vote': avg_vote,
                    'progress_summary': progress_summary,
                    'green_percentage': green_pct,
                    'amber_percentage': amber_pct,
                    'red_percentage': red_pct,
                }
            )

def load_teams(request):
    department_id = request.GET.get('department')
    teams = Team.objects.filter(department_id=department_id).order_by('name')
    return JsonResponse([{'id': team.id, 'name': team.name} for team in teams], safe=False)

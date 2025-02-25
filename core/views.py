from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Case, When, IntegerField, Q, F, Avg
from .forms import UserRegistrationForm, UserProfileForm
from .models import Department, Team, Session, HealthCheckCard, Vote

def home(request):
    departments = Department.objects.all()
    return render(request, 'core/home.html', {'departments': departments})

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'core/register.html', {'form': form})

@login_required
def dashboard(request):
    # Get the latest active session
    latest_session = Session.objects.filter(is_active=True).order_by('-date').first()
    
    # Get the user's team
    user_team = request.user.team
    
    # Get team members if user has a team
    team_members = []
    if user_team:
        team_members = user_team.user_set.all()
    
    # Get cards
    cards = HealthCheckCard.objects.filter(active=True)
    
    # Get user's votes for latest session
    user_votes = []
    if latest_session:
        user_votes = Vote.objects.filter(user=request.user, session=latest_session)
    
    context = {
        'latest_session': latest_session,
        'user_team': user_team,
        'team_members': team_members,
        'cards': cards,
        'user_votes': user_votes,
    }
    
    return render(request, 'core/dashboard.html', context)

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'core/profile.html', {'form': form})

@login_required
def vote(request, session_id, card_id):
    session = get_object_or_404(Session, id=session_id, is_active=True)
    card = get_object_or_404(HealthCheckCard, id=card_id, active=True)
    
    if request.method == 'POST':
        vote_value = request.POST.get('vote')
        comment = request.POST.get('comment', '')
        
        # Create or update vote
        vote_obj, created = Vote.objects.update_or_create(
            user=request.user,
            session=session,
            card=card,
            defaults={'value': vote_value, 'comment': comment}
        )
        
        messages.success(request, f'Vote for {card.name} submitted successfully!')
        return redirect('dashboard')
    
    # Check if user already voted for this card
    try:
        existing_vote = Vote.objects.get(user=request.user, session=session, card=card)
        current_value = existing_vote.value
        current_comment = existing_vote.comment
    except Vote.DoesNotExist:
        current_value = ''
        current_comment = ''
    
    context = {
        'session': session,
        'card': card,
        'current_value': current_value,
        'current_comment': current_comment
    }
    
    return render(request, 'core/vote.html', context)

@login_required
def progress_chart(request):
    # Get all sessions ordered by date
    sessions = Session.objects.all().order_by('date')
    
    # Get user's team
    user_team = request.user.team
    
    # Initialize data
    chart_data = []
    
    if user_team:
        # Get team votes across all sessions
        for session in sessions:
            # Count votes by type for each session
            vote_counts = Vote.objects.filter(
                user__team=user_team,
                session=session
            ).aggregate(
                green=Count(Case(When(value='green', then=1), output_field=IntegerField())),
                amber=Count(Case(When(value='amber', then=1), output_field=IntegerField())),
                red=Count(Case(When(value='red', then=1), output_field=IntegerField()))
            )
            
            # Calculate totals
            total_votes = vote_counts['green'] + vote_counts['amber'] + vote_counts['red']
            
            # Calculate percentages if there are votes
            if total_votes > 0:
                session_data = {
                    'session': session.name,
                    'date': session.date.strftime('%Y-%m-%d'),
                    'green_percent': round((vote_counts['green'] / total_votes) * 100, 1),
                    'amber_percent': round((vote_counts['amber'] / total_votes) * 100, 1),
                    'red_percent': round((vote_counts['red'] / total_votes) * 100, 1),
                }
                chart_data.append(session_data)
    
    return render(request, 'core/progress_chart.html', {'chart_data': chart_data, 'team': user_team})

@login_required
def team_summary(request, team_id=None):
    # If no team_id, use user's team
    if team_id is None and request.user.team:
        team_id = request.user.team.id
    
    # Get the team
    team = None
    if team_id:
        team = get_object_or_404(Team, id=team_id)
    
    # Check permission to view team summary
    if team and not (request.user.team == team or request.user.role in ['team_leader', 'department_leader', 'admin']):
        messages.error(request, 'You do not have permission to view this team summary.')
        return redirect('dashboard')
    
    # Get the latest session
    latest_session = Session.objects.filter(is_active=True).order_by('-date').first()
    
    # Initialize summary data
    summary_data = []
    participation_rate = 0
    
    if team and latest_session:
        # Get all active cards
        cards = HealthCheckCard.objects.filter(active=True)
        
        for card in cards:
            # Get votes for this card from team members
            votes = Vote.objects.filter(
                user__team=team,
                card=card,
                session=latest_session
            )
            
            # Count votes by type
            vote_counts = votes.aggregate(
                green=Count(Case(When(value='green', then=1), output_field=IntegerField())),
                amber=Count(Case(When(value='amber', then=1), output_field=IntegerField())),
                red=Count(Case(When(value='red', then=1), output_field=IntegerField()))
            )
            
            # Calculate totals
            total_votes = vote_counts['green'] + vote_counts['amber'] + vote_counts['red']
            
            # Skip if no votes for this card
            if total_votes == 0:
                continue
            
            # Determine predominant vote
            if vote_counts['green'] >= vote_counts['amber'] and vote_counts['green'] >= vote_counts['red']:
                predominant = 'green'
            elif vote_counts['amber'] >= vote_counts['green'] and vote_counts['amber'] >= vote_counts['red']:
                predominant = 'amber'
            else:
                predominant = 'red'
            
            # Calculate percentages
            green_percent = round((vote_counts['green'] / total_votes) * 100, 1)
            amber_percent = round((vote_counts['amber'] / total_votes) * 100, 1)
            red_percent = round((vote_counts['red'] / total_votes) * 100, 1)
            
            # Get comments
            comments = votes.exclude(comment__isnull=True).exclude(comment='').values('comment', 'value', 'user__username')
            
            card_data = {
                'card': card,
                'green': vote_counts['green'],
                'amber': vote_counts['amber'],
                'red': vote_counts['red'],
                'predominant': predominant,
                'green_percent': green_percent,
                'amber_percent': amber_percent,
                'red_percent': red_percent,
                'comments': comments,
            }
            
            summary_data.append(card_data)
        
        # Calculate participation rate
        team_size = team.user_set.count()
        if team_size > 0:
            participants = Vote.objects.filter(
                user__team=team,
                session=latest_session
            ).values('user').distinct().count()
            
            participation_rate = round((participants / team_size) * 100, 1)
    
    context = {
        'team': team,
        'teams': Team.objects.all().order_by('department__name', 'name'),
        'session': latest_session,
        'summary_data': summary_data,
        'participation_rate': participation_rate,
    }
    
    return render(request, 'core/team_summary.html', context)

@login_required
def department_summary(request, department_id=None):
    # If no department_id, use user's department
    if department_id is None and request.user.department:
        department_id = request.user.department.id
    
    # Get the department
    department = None
    if department_id:
        department = get_object_or_404(Department, id=department_id)
    
    # Check permission to view department summary
    if department and not (request.user.department == department or request.user.role in ['department_leader', 'admin']):
        messages.error(request, 'You do not have permission to view this department summary.')
        return redirect('dashboard')
    
    # Get the latest session
    latest_session = Session.objects.filter(is_active=True).order_by('-date').first()
    
    # Initialize summary data
    teams_data = []
    department_summary = []
    overall_participation = 0
    
    if department and latest_session:
        # Get all teams in the department
        teams = Team.objects.filter(department=department)
        
        # Get all active cards
        cards = HealthCheckCard.objects.filter(active=True)
        
        # Initialize department summary
        for card in cards:
            department_summary.append({
                'card': card,
                'green': 0,
                'amber': 0,
                'red': 0,
                'total': 0,
                'teams': []
            })
        
        # Total users in department
        total_users = department.user_set.count()
        total_participants = 0
        
        # Process each team
        for team in teams:
            team_data = {
                'team': team,
                'cards': [],
                'participation_rate': 0
            }
            
            # Team size
            team_size = team.user_set.count()
            
            # Skip teams with no members
            if team_size == 0:
                continue
            
            # Team participants
            team_participants = Vote.objects.filter(
                user__team=team,
                session=latest_session
            ).values('user').distinct().count()
            
            # Add to total participants
            total_participants += team_participants
            
            # Calculate team participation rate
            team_data['participation_rate'] = round((team_participants / team_size) * 100, 1)
            
            # Process each card for this team
            for card in cards:
                # Get votes for this card from team members
                votes = Vote.objects.filter(
                    user__team=team,
                    card=card,
                    session=latest_session
                )
                
                # Count votes by type
                vote_counts = votes.aggregate(
                    green=Count(Case(When(value='green', then=1), output_field=IntegerField())),
                    amber=Count(Case(When(value='amber', then=1), output_field=IntegerField())),
                    red=Count(Case(When(value='red', then=1), output_field=IntegerField()))
                )
                
                # Calculate totals
                total_votes = vote_counts['green'] + vote_counts['amber'] + vote_counts['red']
                
                # Skip if no votes for this card
                if total_votes == 0:
                    continue
                
                # Determine predominant vote
                if vote_counts['green'] >= vote_counts['amber'] and vote_counts['green'] >= vote_counts['red']:
                    predominant = 'green'
                elif vote_counts['amber'] >= vote_counts['green'] and vote_counts['amber'] >= vote_counts['red']:
                    predominant = 'amber'
                else:
                    predominant = 'red'
                
                # Add to department summary
                for summary in department_summary:
                    if summary['card'] == card:
                        summary['green'] += vote_counts['green']
                        summary['amber'] += vote_counts['amber']
                        summary['red'] += vote_counts['red']
                        summary['total'] += total_votes
                        summary['teams'].append({
                            'team': team,
                            'predominant': predominant
                        })
                
                # Calculate percentages
                green_percent = round((vote_counts['green'] / total_votes) * 100, 1)
                amber_percent = round((vote_counts['amber'] / total_votes) * 100, 1)
                red_percent = round((vote_counts['red'] / total_votes) * 100, 1)
                
                card_data = {
                    'card': card,
                    'green': vote_counts['green'],
                    'amber': vote_counts['amber'],
                    'red': vote_counts['red'],
                    'predominant': predominant,
                    'green_percent': green_percent,
                    'amber_percent': amber_percent,
                    'red_percent': red_percent,
                }
                
                team_data['cards'].append(card_data)
            
            teams_data.append(team_data)
        
        # Calculate overall participation rate
        if total_users > 0:
            overall_participation = round((total_participants / total_users) * 100, 1)
        
        # Calculate percentages for department summary
        for summary in department_summary:
            if summary['total'] > 0:
                summary['green_percent'] = round((summary['green'] / summary['total']) * 100, 1)
                summary['amber_percent'] = round((summary['amber'] / summary['total']) * 100, 1)
                summary['red_percent'] = round((summary['red'] / summary['total']) * 100, 1)
                
                if summary['green'] >= summary['amber'] and summary['green'] >= summary['red']:
                    summary['predominant'] = 'green'
                elif summary['amber'] >= summary['green'] and summary['amber'] >= summary['red']:
                    summary['predominant'] = 'amber'
                else:
                    summary['predominant'] = 'red'
    
    context = {
        'department': department,
        'departments': Department.objects.all().order_by('name'),
        'session': latest_session,
        'teams_data': teams_data,
        'department_summary': department_summary,
        'overall_participation': overall_participation,
    }
    
    return render(request, 'core/department_summary.html', context)

def load_teams(request):
    department_id = request.GET.get('department')
    teams = Team.objects.filter(department_id=department_id).order_by('name')
    return JsonResponse(list(teams.values('id', 'name')), safe=False)

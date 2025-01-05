from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm
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

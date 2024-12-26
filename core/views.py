from django.shortcuts import render, redirect
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

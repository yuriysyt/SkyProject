
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from core.models import Session, HealthCheckCard, Vote, TeamSummary, User, Team, Department
import json

@login_required
@require_http_methods(["GET"])
def active_sessions(request):
    """Return all active sessions"""
    sessions = Session.objects.filter(is_active=True).values('id', 'name', 'description', 'date')
    return JsonResponse({'sessions': list(sessions)})

@login_required
@require_http_methods(["GET"])
def session_cards(request, session_id):
    """Return all cards for a specific session"""
    try:
        session = Session.objects.get(id=session_id)
        # Get all active health check cards
        cards = HealthCheckCard.objects.filter(active=True).values('id', 'name', 'description', 'icon', 'order')
        return JsonResponse({'cards': list(cards)})
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

@login_required
@require_http_methods(["POST"])
def submit_vote(request, session_id, card_id):
    """Submit a vote for a specific card in a session"""
    try:
        data = json.loads(request.body)
        value = data.get('value')
        progress_note = data.get('progress_note', 'same')
        
        session = Session.objects.get(id=session_id)
        card = HealthCheckCard.objects.get(id=card_id)
        
        # Create or update vote
        vote, created = Vote.objects.update_or_create(
            user=request.user,
            card=card,
            session=session,
            defaults={'value': value, 'progress_note': progress_note}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Vote submitted successfully',
            'vote_id': vote.id
        })
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except HealthCheckCard.DoesNotExist:
        return JsonResponse({'error': 'Card not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_http_methods(["GET"])
def team_summary(request, team_id):
    """Return summary data for a specific team"""
    try:
        team = Team.objects.get(id=team_id)
        # Check if user has permission to view this team's data
        if request.user.role not in ['team_leader', 'department_leader', 'senior_manager'] and request.user.team.id != team_id:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        summaries = TeamSummary.objects.filter(team=team).values(
            'id', 'card__name', 'average_vote', 'progress_summary',
            'green_percentage', 'amber_percentage', 'red_percentage'
        )
        return JsonResponse({'team_summaries': list(summaries)})
    except Team.DoesNotExist:
        return JsonResponse({'error': 'Team not found'}, status=404)

@login_required
@require_http_methods(["GET"])
def department_summary(request, department_id):
    """Return summary data for a specific department"""
    try:
        department = Department.objects.get(id=department_id)
        # Check if user has permission to view this department's data
        if request.user.role not in ['department_leader', 'senior_manager'] and (
            not hasattr(request.user, 'department') or request.user.department.id != department_id):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        teams = Team.objects.filter(department=department).values('id', 'name')
        team_data = []
        
        for team in teams:
            summaries = TeamSummary.objects.filter(team_id=team['id']).values(
                'id', 'card__name', 'average_vote', 'progress_summary'
            )
            team_data.append({
                'team': team,
                'summaries': list(summaries)
            })
        
        return JsonResponse({'department_teams': team_data})
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)

@login_required
@require_http_methods(["GET"])
def user_progress(request):
    """Return user's voting progress"""
    user = request.user
    active_sessions = Session.objects.filter(is_active=True)
    
    if not active_sessions:
        return JsonResponse({'error': 'No active sessions'}, status=404)
    
    session = active_sessions.first()
    total_cards = HealthCheckCard.objects.filter(active=True).count()
    user_votes = Vote.objects.filter(user=user, session=session).count()
    
    return JsonResponse({
        'total_cards': total_cards,
        'user_votes': user_votes,
        'completion_percentage': (user_votes / total_cards * 100) if total_cards > 0 else 0
    })

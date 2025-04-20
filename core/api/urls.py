
from django.urls import path
from . import views

urlpatterns = [
    # API endpoints
    path('sessions/', views.active_sessions, name='api_active_sessions'),
    path('cards/<int:session_id>/', views.session_cards, name='api_session_cards'),
    path('vote/<int:session_id>/<int:card_id>/', views.submit_vote, name='api_submit_vote'),
    path('team-summary/<int:team_id>/', views.team_summary, name='api_team_summary'),
    path('department-summary/<int:department_id>/', views.department_summary, name='api_department_summary'),
    path('user-progress/', views.user_progress, name='api_user_progress'),
]

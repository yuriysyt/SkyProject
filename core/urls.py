from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('vote/<int:session_id>/<int:card_id>/', views.vote, name='vote'),
    path('vote-all/<int:session_id>/', views.vote_all, name='vote_all'),
    path('vote-all-submit/<int:session_id>/', views.vote_all_submit, name='vote_all_submit'),
    path('progress-chart/', views.progress_chart, name='progress_chart'),
    path('team-summary/', views.team_summary, name='team_summary'),
    path('team-summary/<int:team_id>/', views.team_summary, name='team_summary_detail'),
    path('department-summary/', views.department_summary, name='department_summary'),
    path('department-summary/<int:department_id>/', views.department_summary, name='department_summary_detail'),
    path('ajax/load-teams/', views.load_teams, name='ajax_load_teams'),
]

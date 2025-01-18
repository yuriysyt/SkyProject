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
    path('vote/<int:session_id>/<int:card_id>/', views.vote, name='vote'),
    path('ajax/load-teams/', views.load_teams, name='ajax_load_teams'),
]

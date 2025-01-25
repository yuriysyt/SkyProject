from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

class ProtectedView(LoginRequiredMixin, ListView):
    login_url = '/login/'
    redirect_field_name = 'next'


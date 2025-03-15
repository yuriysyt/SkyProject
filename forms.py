from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    department = forms.CharField(max_length=100)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'department', 'password1', 'password2')

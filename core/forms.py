from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Department, Team

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'department', 'team')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.all()
        self.fields['team'].queryset = Team.objects.none()
        
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['team'].queryset = Team.objects.filter(department_id=department_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.department:
            self.fields['team'].queryset = Team.objects.filter(department=self.instance.department)

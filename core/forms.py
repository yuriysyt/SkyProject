from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from .models import User, Vote, Session, Team, Department, HealthCheckCard

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role', 'department', 'team', 'first_name', 'last_name')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove admin from role choices
        self.fields['role'].choices = [choice for choice in User.ROLES if choice[0] != 'admin']
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

class UserProfileForm(UserChangeForm):
    password = None  # Remove password field from form
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'department', 'team', 'profile_picture', 'bio')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }
        
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

class VoteForm(forms.ModelForm):
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional comment'}))
    
    class Meta:
        model = Vote
        fields = ('value', 'progress_note', 'comment')
        widgets = {
            'value': forms.RadioSelect(),
            'progress_note': forms.RadioSelect()
        }
        labels = {
            'value': 'How do you rate this area?',
            'progress_note': 'Is this area improving?'
        }

class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ('name', 'date', 'description', 'is_active')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ('name', 'department', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ('name', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class HealthCheckCardForm(forms.ModelForm):
    class Meta:
        model = HealthCheckCard
        fields = ('name', 'description', 'icon', 'order', 'active')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class SessionSelectionForm(forms.Form):
    session = forms.ModelChoiceField(
        queryset=Session.objects.filter(is_active=True),
        empty_label="Select a session",
        required=True
    )

class DateRangeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
class TeamSelectionForm(forms.Form):
    team = forms.ModelChoiceField(
        queryset=Team.objects.all(),
        empty_label="Select a team",
        required=True
    )
    
    def __init__(self, department=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if department:
            self.fields['team'].queryset = Team.objects.filter(department=department)

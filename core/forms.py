"""
Forms for the Health Check System.

This module defines the forms used throughout the health check system for data input,
editing, and filtering. Forms are organized by their related models and functionality.

Key components:
- User forms: Registration and profile management
- Health check forms: Voting and session management
- Organization forms: Team and department management
- Utility forms: Selection and filtering forms for views

Forms implement various validation rules and dynamic field behavior to ensure
data integrity and improve user experience.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from .models import User, Vote, Session, Team, Department, HealthCheckCard

class UserRegistrationForm(UserCreationForm):
    """
    Form for registering new users in the health check system.
    
    This form extends Django's UserCreationForm to include additional fields
    specific to the health check system, such as role, department, and team.
    It also implements dynamic behavior for the team field, which is filtered
    based on the selected department.
    
    The form prevents users from registering with the 'admin' role, which
    can only be assigned through the Django admin interface for security.
    
    This form is used in the registration view and by administrators when
    creating new user accounts.
    """
    # Make email a required field (not required by default in UserCreationForm)
    email = forms.EmailField(required=True)
    
    class Meta:
        """
        Meta options for the UserRegistrationForm.
        
        - model: Uses the custom User model
        - fields: Specifies which fields to include in the form
        """
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role', 'department', 'team', 'first_name', 'last_name')
        
    def __init__(self, *args, **kwargs):
        """
        Initialize the UserRegistrationForm with dynamic field behavior.
        
        This method customizes the form initialization to:
        1. Remove the 'admin' role from available choices for security
        2. Set up the department dropdown with all departments
        3. Initialize the team dropdown as empty
        4. Implement dynamic filtering of teams based on selected department
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        super().__init__(*args, **kwargs)
        # Remove admin from role choices for security
        self.fields['role'].choices = [choice for choice in User.ROLES if choice[0] != 'admin']
        
        # Initialize department dropdown with all departments
        self.fields['department'].queryset = Department.objects.all()
        
        # Initialize team dropdown as empty (will be populated based on department)
        self.fields['team'].queryset = Team.objects.none()
        
        # If a department is selected in the form data, filter teams accordingly
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['team'].queryset = Team.objects.filter(department_id=department_id)
            except (ValueError, TypeError):
                pass
        # If editing an existing user, show teams from their current department
        elif self.instance.pk and self.instance.department:
            self.fields['team'].queryset = Team.objects.filter(department=self.instance.department)

class UserProfileForm(UserChangeForm):
    """
    Form for editing user profiles in the health check system.
    
    This form extends Django's UserChangeForm but removes the password field,
    as password changes are handled through a separate form. It allows users
    to update their personal information, department and team assignments,
    profile picture, and biographical information.
    
    Like the registration form, it implements dynamic behavior for the team field,
    which is filtered based on the selected department.
    
    This form is used in the profile edit view, allowing users to update their
    information after registration.
    """
    # Remove password field from form (password changes are handled separately)
    password = None
    
    class Meta:
        """
        Meta options for the UserProfileForm.
        
        - model: Uses the custom User model
        - fields: Specifies which fields to include in the form
        - widgets: Customizes the form widgets for specific fields
        """
        model = User
        fields = ('first_name', 'last_name', 'email', 'department', 'team', 'profile_picture', 'bio')
        widgets = {
            # Use a larger textarea for the bio field
            'bio': forms.Textarea(attrs={'rows': 4}),
        }
        
    def __init__(self, *args, **kwargs):
        """
        Initialize the UserProfileForm with dynamic field behavior.
        
        This method customizes the form initialization to:
        1. Set up the department dropdown with all departments
        2. Initialize the team dropdown as empty
        3. Implement dynamic filtering of teams based on selected department
        
        The behavior is similar to the registration form but without the
        role field restrictions.
        
        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        super().__init__(*args, **kwargs)
        
        # Initialize department dropdown with all departments
        self.fields['department'].queryset = Department.objects.all()
        
        # Initialize team dropdown as empty (will be populated based on department)
        self.fields['team'].queryset = Team.objects.none()
        
        # If a department is selected in the form data, filter teams accordingly
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['team'].queryset = Team.objects.filter(department_id=department_id)
            except (ValueError, TypeError):
                pass
        # If editing an existing user, show teams from their current department
        elif self.instance.pk and self.instance.department:
            self.fields['team'].queryset = Team.objects.filter(department=self.instance.department)

class VoteForm(forms.ModelForm):
    """
    Form for submitting votes in health check sessions.
    
    This form allows users to submit their assessment of a health check card
    using the traffic light system (green, amber, red), along with a progress
    indicator (better, same, worse) and an optional comment.
    
    The form uses radio buttons for the traffic light and progress selections
    to make the options visually clear. The comment field is optional and uses
    a textarea for longer text input.
    
    This form is used in both individual voting views and in the bulk voting
    view where users can vote on all cards at once.
    """
    # Override the comment field to customize its widget
    comment = forms.CharField(
        required=False,  # Comments are optional
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional comment'})
    )
    
    class Meta:
        """
        Meta options for the VoteForm.
        
        - model: Uses the Vote model
        - fields: Specifies which fields to include in the form
        - widgets: Customizes the form widgets for specific fields
        - labels: Provides user-friendly labels for form fields
        """
        model = Vote
        fields = ('value', 'progress_note', 'comment')
        widgets = {
            # Use radio buttons for clearer visual selection
            'value': forms.RadioSelect(),
            'progress_note': forms.RadioSelect()
        }
        labels = {
            # User-friendly question labels
            'value': 'How do you rate this area?',
            'progress_note': 'Is this area improving?'
        }

class SessionForm(forms.ModelForm):
    """
    Form for creating and editing health check sessions.
    
    This form allows administrators and authorized users to create new health check
    sessions or edit existing ones. Sessions are time-bounded periods when users can
    submit votes for health check cards.
    
    The form includes fields for the session name, date, description, and active status.
    It uses a date picker for the date field and a textarea for the description to
    improve user experience.
    
    This form is used in the session management views, accessible to users with
    appropriate permissions (typically admins and department leaders).
    """
    class Meta:
        """
        Meta options for the SessionForm.
        
        - model: Uses the Session model
        - fields: Specifies which fields to include in the form
        - widgets: Customizes the form widgets for specific fields
        """
        model = Session
        fields = ('name', 'date', 'description', 'is_active')
        widgets = {
            # Use HTML5 date picker for better date selection
            'date': forms.DateInput(attrs={'type': 'date'}),
            # Use a larger textarea for the description
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class TeamForm(forms.ModelForm):
    """
    Form for creating and editing teams in the health check system.
    
    This form allows administrators and department leaders to create new teams
    or edit existing ones. Teams are mid-level organizational units that belong
    to departments and contain users.
    
    The form includes fields for the team name, department assignment, and description.
    It uses a textarea for the description to allow for longer text input.
    
    This form is used in the team management views, accessible to users with
    appropriate permissions (typically admins, department leaders, and team leaders).
    """
    class Meta:
        """
        Meta options for the TeamForm.
        
        - model: Uses the Team model
        - fields: Specifies which fields to include in the form
        - widgets: Customizes the form widgets for specific fields
        """
        model = Team
        fields = ('name', 'department', 'description')
        widgets = {
            # Use a larger textarea for the description
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class DepartmentForm(forms.ModelForm):
    """
    Form for creating and editing departments in the health check system.
    
    This form allows administrators and senior managers to create new departments
    or edit existing ones. Departments are top-level organizational units that
    contain teams and users.
    
    The form includes fields for the department name and description. It uses
    a textarea for the description to allow for longer text input.
    
    This form is used in the department management views, accessible to users with
    appropriate permissions (typically admins and senior managers).
    """
    class Meta:
        """
        Meta options for the DepartmentForm.
        
        - model: Uses the Department model
        - fields: Specifies which fields to include in the form
        - widgets: Customizes the form widgets for specific fields
        """
        model = Department
        fields = ('name', 'description')
        widgets = {
            # Use a larger textarea for the description
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class HealthCheckCardForm(forms.ModelForm):
    """
    Form for creating and editing health check cards in the system.
    
    This form allows administrators to create new health check cards or edit
    existing ones. Health check cards define the specific categories or aspects
    that users vote on during health check sessions (e.g., "Team Morale",
    "Technical Debt", "Delivery Pace").
    
    The form includes fields for the card name, description, icon, display order,
    and active status. It uses a textarea for the description to allow for
    detailed explanations of what each card represents.
    
    This form is used in the card management views, accessible to users with
    administrative permissions.
    """
    class Meta:
        """
        Meta options for the HealthCheckCardForm.
        
        - model: Uses the HealthCheckCard model
        - fields: Specifies which fields to include in the form
        - widgets: Customizes the form widgets for specific fields
        """
        model = HealthCheckCard
        fields = ('name', 'description', 'icon', 'order', 'active')
        widgets = {
            # Use a larger textarea for the description
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class SessionSelectionForm(forms.Form):
    """
    Form for selecting a session in various views.
    
    This utility form provides a dropdown for selecting an active health check
    session. It's used in multiple views where data needs to be filtered by session,
    such as voting forms, team summaries, and department summaries.
    
    By default, it only shows active sessions to focus on current health checks.
    """
    session = forms.ModelChoiceField(
        queryset=Session.objects.filter(is_active=True),  # Only show active sessions
        empty_label="Select a session",  # Default empty option text
        required=True  # A session must be selected
    )

class DateRangeForm(forms.Form):
    """
    Form for selecting a date range in reporting views.
    
    This utility form provides date pickers for selecting start and end dates
    for filtering data in reports and charts. It's used in trend analysis views
    and historical data reports.
    
    The form uses HTML5 date pickers for better user experience.
    """
    # Start date with HTML5 date picker
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    # End date with HTML5 date picker
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
class TeamSelectionForm(forms.Form):
    """
    Form for selecting a team in various views.
    
    This utility form provides a dropdown for selecting a team. It's used in
    multiple views where data needs to be filtered by team, such as team summaries
    and participation reports.
    
    The form can be initialized with a department parameter to filter the teams
    shown in the dropdown, making it easier to find the relevant team.
    """
    team = forms.ModelChoiceField(
        queryset=Team.objects.all(),  # Default to all teams
        empty_label="Select a team",  # Default empty option text
        required=True  # A team must be selected
    )
    
    def __init__(self, department=None, *args, **kwargs):
        """
        Initialize the TeamSelectionForm with optional department filtering.
        
        This method customizes the form initialization to filter the team
        dropdown based on the provided department, if any.
        
        Args:
            department: Optional Department object to filter teams by
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        super().__init__(*args, **kwargs)
        # If a department is provided, filter teams to only show those in that department
        if department:
            self.fields['team'].queryset = Team.objects.filter(department=department)

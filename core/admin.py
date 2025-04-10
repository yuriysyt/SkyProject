from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Department, Team, HealthCheckCard, Vote

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('username', 'email', 'department', 'team', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('department', 'team')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('department', 'team')}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Department)
admin.site.register(Team)
admin.site.register(HealthCheckCard)
admin.site.register(Vote)

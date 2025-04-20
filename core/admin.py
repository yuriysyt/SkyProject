
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Department, Team, Session, 
    HealthCheckCard, Vote, TeamSummary, DepartmentSummary
)

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'team', 'is_active')
    list_filter = ('role', 'department', 'team', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'bio', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Organization', {'fields': ('role', 'department', 'team')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'department', 'team'),
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_team_count', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'get_member_count', 'created_at')
    list_filter = ('department',)
    search_fields = ('name', 'department__name')
    readonly_fields = ('created_at',)


class SessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'is_active', 'created_at')
    list_filter = ('is_active', 'date')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)


class HealthCheckCardAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'active')
    list_filter = ('active',)
    search_fields = ('name', 'description')
    ordering = ('order',)


class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'card', 'session', 'value', 'progress_note', 'created_at')
    list_filter = ('value', 'progress_note', 'session', 'card')
    search_fields = ('user__username', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


class TeamSummaryAdmin(admin.ModelAdmin):
    list_display = ('team', 'session', 'card', 'average_vote', 'progress_summary')
    list_filter = ('average_vote', 'progress_summary', 'team', 'session', 'card')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


class DepartmentSummaryAdmin(admin.ModelAdmin):
    list_display = ('department', 'session', 'card', 'average_vote', 'progress_summary')
    list_filter = ('average_vote', 'progress_summary', 'department', 'session', 'card')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


# Register all models with their custom admin classes
admin.site.register(User, CustomUserAdmin)
admin.site.register(Department, DepartmentAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(HealthCheckCard, HealthCheckCardAdmin)
admin.site.register(Vote, VoteAdmin)
admin.site.register(TeamSummary, TeamSummaryAdmin)
admin.site.register(DepartmentSummary, DepartmentSummaryAdmin)

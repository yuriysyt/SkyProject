
from django import template
from django.db.models import Count
from ..models import Department, Team

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Gets an item from a dictionary by key.
    Usage: {{ dictionary|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.simple_tag
def get_departments_count():
    """
    Returns the count of departments.
    Usage: {% get_departments_count %}
    """
    return Department.objects.count()

@register.simple_tag
def get_teams_count():
    """
    Returns the count of teams.
    Usage: {% get_teams_count %}
    """
    return Team.objects.count()

@register.simple_tag
def get_teams_by_department(department_id):
    """
    Returns teams for a specific department.
    Usage: {% get_teams_by_department department.id as teams %}
    """
    return Team.objects.filter(department_id=department_id)

@register.simple_tag
def department_has_teams(department_id):
    """
    Checks if a department has teams.
    Usage: {% department_has_teams department.id as has_teams %}
    """
    return Team.objects.filter(department_id=department_id).exists()

@register.filter
def multiply(value, arg):
    """
    Multiplies the value by the argument.
    Usage: {{ value|multiply:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """
    Divides the value by the argument.
    Usage: {{ value|divide:arg }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def subtract(value, arg):
    """
    Subtracts the argument from the value.
    Usage: {{ value|subtract:arg }}
    """
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value):
    """
    Formats a value as a percentage with 1 decimal place.
    Usage: {{ value|percentage }}
    """
    try:
        return f"{float(value):.1f}%"
    except (ValueError, TypeError):
        return "0.0%"

@register.filter
def to_list(value):
    """
    Converts a value to a list.
    Usage: {{ value|to_list }}
    """
    if isinstance(value, list):
        return value
    return [value]

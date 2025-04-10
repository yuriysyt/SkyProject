from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from core.models import User, Team, Department, Session, HealthCheckCard, Vote
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import HealthCheck, Department, Category
import random
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Generates realistic health check data for the last N days'
    
    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Number of days to generate data for')
        parser.add_argument('--per-day', type=int, default=5, help='Average number of entries per day')
    
    def handle(self, *args, **options):
        days = options['days']
        per_day = options['per_day']
        
        self.stdout.write(f'Generating health check data for the last {days} days...')
        
        # Get all users, departments and categories
        users = list(User.objects.all())
        departments = list(Department.objects.all())
        categories = list(Category.objects.all())
        
        if not users or not departments or not categories:
            self.stdout.write(self.style.ERROR('Cannot generate data: missing users, departments or categories'))
            return
        
        # Generate data for each day
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        current_date = start_date
        
        total_created = 0
        
        while current_date <= end_date:
            # Randomize the number of entries for this day
            daily_count = random.randint(max(1, per_day - 2), per_day + 2)
            
            for _ in range(daily_count):
                user = random.choice(users)
                department = random.choice(departments)
                category = random.choice(categories)
                score = random.randint(1, 5)
                
                # Create a timestamp within the current day
                hour = random.randint(8, 17)  # Business hours
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                timestamp = current_date.replace(hour=hour, minute=minute, second=second)
                
                # Generate a comment based on the score
                comments = {
                    1: ['Significant issues observed', 'Needs immediate attention', 'Critical problems identified'],
                    2: ['Several problems identified', 'Below expectations', 'Requires improvement'],
                    3: ['Average performance', 'Some minor issues', 'Acceptable but could be better'],
                    4: ['Good overall', 'Minor improvements possible', 'Working well with few issues'],
                    5: ['Excellent condition', 'Outstanding performance', 'No issues identified']
                }
                comment = random.choice(comments[score])
                
                # Create the health check entry
                HealthCheck.objects.create(
                    user=user,
                    department=department,
                    category=category,
                    score=score,
                    comment=comment,
                    created_at=timestamp
                )
                total_created += 1
            
            # Move to the next day
            current_date += timedelta(days=1)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully generated {total_created} health check entries'))


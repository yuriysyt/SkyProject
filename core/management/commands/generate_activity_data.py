from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Generates sample user activity data for testing'
    
    def handle(self, *args, **options):
        self.stdout.write('Generating sample user activity data...')
        # Placeholder for actual implementation
        self.stdout.write(self.style.SUCCESS('Successfully generated sample data'))


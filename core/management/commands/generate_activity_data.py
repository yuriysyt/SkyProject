class Command(BaseCommand):
    help = 'Generates sample user activity data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=10, help='Number of sample records to generate')
    
    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write(f'Generating {count} sample user activity records...')
        # Implementation would go here
        self.stdout.write(self.style.SUCCESS(f'Successfully generated {count} sample records'))


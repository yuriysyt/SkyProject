
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Department, Team, HealthCheckCard, Session

class Command(BaseCommand):
    help = 'Creates sample data for the Health Check system'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        
        # Create departments
        self.stdout.write('Creating departments...')
        departments = [
            Department(name="Software Engineering", description="Software development team responsible for core features"),
            Department(name="DevOps", description="Infrastructure and deployment team"),
            Department(name="QA", description="Quality assurance team"),
        ]
        Department.objects.bulk_create(departments)
        
        # Create teams
        self.stdout.write('Creating teams...')
        software_teams = [
            Team(name="Frontend Team", department=departments[0], description="Responsible for UI development"),
            Team(name="Backend Team", department=departments[0], description="Responsible for API development"),
            Team(name="Mobile Team", department=departments[0], description="Responsible for mobile app development"),
        ]
        
        devops_teams = [
            Team(name="Cloud Infrastructure", department=departments[1], description="Manages cloud resources"),
            Team(name="CI/CD", department=departments[1], description="Manages continuous integration and deployment"),
        ]
        
        qa_teams = [
            Team(name="Automated Testing", department=departments[2], description="Develops and maintains automated tests"),
            Team(name="Manual Testing", department=departments[2], description="Performs manual testing and UX evaluation"),
        ]
        
        Team.objects.bulk_create(software_teams + devops_teams + qa_teams)
        
        # Create health check cards
        self.stdout.write('Creating health check cards...')
        cards = [
            HealthCheckCard(name="Codebase Health", description="Quality and maintainability of the codebase", icon="code", order=1),
            HealthCheckCard(name="Testing", description="Test coverage and quality", icon="flask-vial", order=2),
            HealthCheckCard(name="Release Process", description="Efficiency of releasing features", icon="rocket", order=3),
            HealthCheckCard(name="Stakeholder Relationships", description="Communication with stakeholders", icon="users", order=4),
            HealthCheckCard(name="Team Velocity", description="Team's ability to deliver consistently", icon="gauge-high", order=5),
            HealthCheckCard(name="Technical Debt", description="Level of debt that needs to be addressed", icon="credit-card", order=6),
            HealthCheckCard(name="Documentation", description="Quality and completeness of documentation", icon="file-lines", order=7),
            HealthCheckCard(name="Learning & Growth", description="Team's ability to learn and adapt", icon="graduation-cap", order=8),
            HealthCheckCard(name="Support Quality", description="Quality of support provided to users/customers", icon="headset", order=9),
            HealthCheckCard(name="Team Morale", description="Overall happiness and motivation level", icon="face-smile", order=10),
        ]
        HealthCheckCard.objects.bulk_create(cards)
        
        # Create sessions
        self.stdout.write('Creating health check sessions...')
        today = timezone.now().date()
        
        sessions = [
            Session(name="April 2025 Health Check", date=today, description="Monthly health check for April 2025", is_active=True),
            Session(name="March 2025 Health Check", date=today - timezone.timedelta(days=30), description="Monthly health check for March 2025", is_active=False),
            Session(name="February 2025 Health Check", date=today - timezone.timedelta(days=60), description="Monthly health check for February 2025", is_active=False),
        ]
        Session.objects.bulk_create(sessions)
        
        # Create sample admin user if not exists
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin', 
                email='admin@example.com', 
                password='adminpassword',
                role='admin'
            )
            self.stdout.write('Created superuser: admin (password: adminpassword)')
        
        # Create sample department leader
        if not User.objects.filter(username='deptleader').exists():
            dept_leader = User.objects.create_user(
                username='deptleader',
                email='deptleader@example.com',
                password='password123',
                role='department_leader',
                department=departments[0],
                first_name='Department',
                last_name='Leader'
            )
            self.stdout.write('Created department leader: deptleader (password: password123)')
        
        # Create sample team leader
        if not User.objects.filter(username='teamleader').exists():
            team_leader = User.objects.create_user(
                username='teamleader',
                email='teamleader@example.com',
                password='password123',
                role='team_leader',
                department=departments[0],
                team=software_teams[0],
                first_name='Team',
                last_name='Leader'
            )
            self.stdout.write('Created team leader: teamleader (password: password123)')
        
        # Create sample engineer
        if not User.objects.filter(username='engineer').exists():
            engineer = User.objects.create_user(
                username='engineer',
                email='engineer@example.com',
                password='password123',
                role='engineer',
                department=departments[0],
                team=software_teams[0],
                first_name='Sample',
                last_name='Engineer'
            )
            self.stdout.write('Created engineer: engineer (password: password123)')
            
        self.stdout.write(self.style.SUCCESS('Successfully created sample data!'))
        self.stdout.write('You can now login with the following credentials:')
        self.stdout.write('  Admin: username=admin, password=adminpassword')
        self.stdout.write('  Department Leader: username=deptleader, password=password123')
        self.stdout.write('  Team Leader: username=teamleader, password=password123')
        self.stdout.write('  Engineer: username=engineer, password=password123')


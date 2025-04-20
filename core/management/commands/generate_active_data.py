
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from core.models import (
    User, Team, Department, Session, HealthCheckCard,
    Vote, TeamSummary, DepartmentSummary
)
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Generates active data with users, teams, departments, and active sessions'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample data for the health check system...')
        
        # Create departments
        departments = []
        dept_names = ['Engineering', 'Product', 'Marketing', 'Customer Support', 'Finance']
        
        for name in dept_names:
            dept, created = Department.objects.get_or_create(
                name=name,
                defaults={
                    'description': f'{name} department responsible for {name.lower()} activities.'
                }
            )
            departments.append(dept)
            action = 'Created' if created else 'Found existing'
            self.stdout.write(f'{action} department: {name}')
        
        # Create teams for each department
        teams = []
        for dept in departments:
            # Create 2-3 teams per department
            num_teams = random.randint(2, 3)
            for i in range(1, num_teams + 1):
                team_name = f'{dept.name} Team {i}'
                team, created = Team.objects.get_or_create(
                    name=team_name,
                    department=dept,
                    defaults={
                        'description': f'Team {i} in the {dept.name} department.'
                    }
                )
                teams.append(team)
                action = 'Created' if created else 'Found existing'
                self.stdout.write(f'{action} team: {team_name}')
        
        # Create health check cards
        cards = []
        card_data = [
            {
                'name': 'Team Collaboration',
                'description': 'How well does the team collaborate and communicate?',
                'icon': 'bi bi-people',
                'order': 1
            },
            {
                'name': 'Technical Quality',
                'description': 'How is the quality of our technical solutions and code?',
                'icon': 'bi bi-code-square',
                'order': 2
            },
            {
                'name': 'Project Management',
                'description': 'How well are our projects planned and executed?',
                'icon': 'bi bi-kanban',
                'order': 3
            },
            {
                'name': 'Learning & Growth',
                'description': 'Are we continuously learning and improving our skills?',
                'icon': 'bi bi-graph-up',
                'order': 4
            },
            {
                'name': 'Customer Focus',
                'description': 'How well do we understand and address customer needs?',
                'icon': 'bi bi-bullseye',
                'order': 5
            },
            {
                'name': 'Code Review Process',
                'description': 'How effective is our code review process?',
                'icon': 'bi bi-code-slash',
                'order': 6
            },
            {
                'name': 'DevOps Practices',
                'description': 'How well are we implementing DevOps practices?',
                'icon': 'bi bi-gear',
                'order': 7
            },
            {
                'name': 'Documentation',
                'description': 'How complete and useful is our documentation?',
                'icon': 'bi bi-file-text',
                'order': 8
            },
            {
                'name': 'Work-Life Balance',
                'description': 'How is the team\'s work-life balance?',
                'icon': 'bi bi-life-preserver',
                'order': 9
            },
            {
                'name': 'Innovation',
                'description': 'How well do we foster and implement innovation?',
                'icon': 'bi bi-lightbulb',
                'order': 10
            }
        ]
        
        for data in card_data:
            card, created = HealthCheckCard.objects.get_or_create(
                name=data['name'],
                defaults={
                    'description': data['description'],
                    'icon': data['icon'],
                    'order': data['order'],
                    'active': True
                }
            )
            cards.append(card)
            action = 'Created' if created else 'Found existing'
            self.stdout.write(f'{action} health check card: {data["name"]}')
        
        # Create sessions (past and current)
        sessions = []
        today = timezone.now().date()
        
        # Create 3 past sessions
        for i in range(3, 0, -1):
            session_date = today - timedelta(days=i * 30)
            session_name = f'Monthly Health Check {session_date.strftime("%B %Y")}'
            session, created = Session.objects.get_or_create(
                date=session_date,
                defaults={
                    'name': session_name,
                    'description': f'Monthly health check session for {session_date.strftime("%B %Y")}',
                    'is_active': False
                }
            )
            sessions.append(session)
            action = 'Created' if created else 'Found existing'
            self.stdout.write(f'{action} past session: {session_name}')
        
        # Create current active session
        current_session_name = f'Monthly Health Check {today.strftime("%B %Y")}'
        current_session, created = Session.objects.get_or_create(
            date=today,
            defaults={
                'name': current_session_name,
                'description': f'Current monthly health check session for {today.strftime("%B %Y")}',
                'is_active': True
            }
        )
        sessions.append(current_session)
        action = 'Created' if created else 'Found existing'
        self.stdout.write(f'{action} current active session: {current_session_name}')
        
        # Ensure current session is active (even if it already existed)
        if not created:
            current_session.is_active = True
            current_session.save()
            self.stdout.write(f'Updated session {current_session_name} to be active')
        
        # Create users for each team
        default_password = make_password('password123')
        
        # Admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'password': default_password,
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Admin',
                'last_name': 'User'
            }
        )
        action = 'Created' if created else 'Found existing'
        self.stdout.write(f'{action} admin user: admin@example.com')
        
        # Create one senior manager
        senior_manager, created = User.objects.get_or_create(
            username='seniormanager',
            defaults={
                'email': 'seniormanager@example.com',
                'password': default_password,
                'role': 'senior_manager',
                'first_name': 'Senior',
                'last_name': 'Manager'
            }
        )
        action = 'Created' if created else 'Found existing'
        self.stdout.write(f'{action} senior manager: seniormanager@example.com')
        
        # Create department leaders
        for dept in departments:
            username = f"deptleader_{dept.name.lower().replace(' ', '')}"
            dept_leader, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'password': default_password,
                    'role': 'department_leader',
                    'department': dept,
                    'first_name': f'{dept.name}',
                    'last_name': 'Leader'
                }
            )
            action = 'Created' if created else 'Found existing'
            self.stdout.write(f'{action} department leader: {username}@example.com')
        
        # Create team leaders and engineers
        for team in teams:
            # Team leader
            team_leader_username = f"teamleader_{team.name.lower().replace(' ', '')}"
            team_leader, created = User.objects.get_or_create(
                username=team_leader_username[:30],  # Ensure username is not too long
                defaults={
                    'email': f'{team_leader_username[:30]}@example.com',
                    'password': default_password,
                    'role': 'team_leader',
                    'department': team.department,
                    'team': team,
                    'first_name': f'{team.name}',
                    'last_name': 'Leader'
                }
            )
            action = 'Created' if created else 'Found existing'
            self.stdout.write(f'{action} team leader: {team_leader_username[:30]}@example.com')
            
            # Engineers (3-5 per team)
            num_engineers = random.randint(3, 5)
            for i in range(1, num_engineers + 1):
                eng_username = f"engineer_{team.name.lower().replace(' ', '')}_{i}"
                engineer, created = User.objects.get_or_create(
                    username=eng_username[:30],  # Ensure username is not too long
                    defaults={
                        'email': f'{eng_username[:30]}@example.com',
                        'password': default_password,
                        'role': 'engineer',
                        'department': team.department,
                        'team': team,
                        'first_name': f'Engineer {i}',
                        'last_name': f'Team {team.name}'
                    }
                )
                action = 'Created' if created else 'Found existing'
                self.stdout.write(f'{action} engineer: {eng_username[:30]}@example.com')
                
                # Create votes for past sessions
                for session in sessions:
                    for card in cards:
                        # Skip some votes randomly to simulate incomplete data
                        if random.random() > 0.7:
                            continue
                            
                        vote_value = random.choice(['green', 'amber', 'red'])
                        progress = random.choice(['better', 'same', 'worse'])
                        
                        vote, vote_created = Vote.objects.get_or_create(
                            user=engineer,
                            session=session,
                            card=card,
                            defaults={
                                'value': vote_value,
                                'progress_note': progress,
                                'comment': f'Automated sample comment for {card.name}' if random.random() > 0.5 else ''
                            }
                        )
                        
                        if vote_created:
                            self.stdout.write(f'Created vote for {engineer.username} on {card.name} in {session.name}')
        
        # Update team and department summaries
        for session in sessions:
            for card in cards:
                for team in teams:
                    # Update team summary
                    from core.views import update_team_summary
                    update_team_summary(team, session, card)
                    self.stdout.write(f'Updated team summary for {team.name} on {card.name} in {session.name}')
        
        # Complete message
        self.stdout.write(self.style.SUCCESS('Successfully created all sample data!'))
        
        # Print login information
        self.stdout.write('\nYou can now log in with the following accounts:')
        self.stdout.write('  Admin: username=admin, password=password123')
        self.stdout.write('  Senior Manager: username=seniormanager, password=password123')
        self.stdout.write('  Department Leaders: username=deptleader_<departmentname>, password=password123')
        self.stdout.write('  Team Leaders: username=teamleader_<teamname>, password=password123')
        self.stdout.write('  Engineers: username=engineer_<teamname>_<number>, password=password123')
        self.stdout.write('\nExample users:')
        self.stdout.write(f'  Department Leader: username=deptleader_{departments[0].name.lower().replace(" ", "")}, password=password123')
        self.stdout.write(f'  Team Leader: username=teamleader_{teams[0].name.lower().replace(" ", "")[:20]}, password=password123')
        self.stdout.write(f'  Engineer: username=engineer_{teams[0].name.lower().replace(" ", "")[:20]}_1, password=password123')

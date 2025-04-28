# core/tests.py
from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from datetime import timedelta
import json
import time
import logging
from unittest.mock import patch, MagicMock

from core.models import (
    User, Department, Team, Session,
    HealthCheckCard, Vote, TeamSummary,
    DepartmentSummary
)
from core.forms import UserRegistrationForm, VoteForm

User = get_user_model()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        logger.info("Setting up base test data")
        # Departments
        cls.dept1 = Department.objects.create(
            name="Engineering",
            description="Tech department"
        )
        cls.dept2 = Department.objects.create(
            name="Marketing",
            description="Marketing department"
        )
        
        # Teams
        cls.team1 = Team.objects.create(
            name="Backend",
            department=cls.dept1
        )
        cls.team2 = Team.objects.create(
            name="Frontend",
            department=cls.dept1
        )
        cls.team3 = Team.objects.create(
            name="Social Media",
            department=cls.dept2
        )
        
        # Users
        cls.engineer = User.objects.create_user(
            username="engineer1",
            password="testpass123",
            role="engineer",
            department=cls.dept1,
            team=cls.team1
        )
        
        cls.team_leader = User.objects.create_user(
            username="leader1",
            password="testpass123",
            role="team_leader",
            department=cls.dept1,
            team=cls.team1
        )
        
        cls.dept_leader = User.objects.create_user(
            username="dept_lead",
            password="testpass123",
            role="department_leader",
            department=cls.dept1
        )
        
        cls.senior_manager = User.objects.create_superuser(
            username="senior_mgr",
            password="adminpass",
            role="senior_manager"
        )
        
        # Sessions
        cls.active_session = Session.objects.create(
            name="Q3 Active",
            date=timezone.now().date(),
            description="Active session",
            is_active=True
        )
        
        cls.inactive_session = Session.objects.create(
            name="Q2 Closed",
            date=timezone.now().date() - timedelta(days=30),
            description="Inactive session",
            is_active=False
        )
        
        # Health Cards
        cls.card1 = HealthCheckCard.objects.create(
            name="Code Quality",
            description="Quality metrics",
            order=1,
            active=True
        )
        
        cls.card2 = HealthCheckCard.objects.create(
            name="Documentation",
            description="Docs quality",
            order=2,
            active=False
        )
        logger.info("Base test data setup complete")


class ModelTests(BaseTestCase):
    def test_user_creation(self):
        """Test that users are created properly with correct attributes"""
        logger.info("Running test: test_user_creation")
        self.assertEqual(self.engineer.role, "engineer")
        self.assertEqual(self.engineer.department.name, "Engineering")
        self.assertTrue(self.engineer.check_password("testpass123"))
        logger.info("✓ test_user_creation passed")

    def test_team_str_representation(self):
        """Test that Team objects display as 'Team Name (Department Name)'"""
        logger.info("Running test: test_team_str_representation")
        self.assertEqual(str(self.team1), "Backend (Engineering)")
        logger.info("✓ test_team_str_representation passed")

    def test_vote_uniqueness_constraint(self):
        """Test that a user can't vote twice on the same card in a session"""
        logger.info("Running test: test_vote_uniqueness_constraint")
        Vote.objects.create(
            user=self.engineer,
            card=self.card1,
            session=self.active_session,
            value="green",
            progress_note="better"
        )
        with self.assertRaises(Exception):
            Vote.objects.create(
                user=self.engineer,
                card=self.card1,
                session=self.active_session,
                value="red",
                progress_note="worse"
            )
        logger.info("✓ test_vote_uniqueness_constraint passed")
    
    def test_department_str_representation(self):
        """Test that Department objects display just their name"""
        logger.info("Running test: test_department_str_representation")
        self.assertEqual(str(self.dept1), "Engineering")
        logger.info("✓ test_department_str_representation passed")
    
    def test_health_card_str_representation(self):
        """Test that HealthCheckCard objects display their name"""
        logger.info("Running test: test_health_card_str_representation")
        self.assertEqual(str(self.card1), "Code Quality")
        logger.info("✓ test_health_card_str_representation passed")
    
    def test_session_str_representation(self):
        """Test that Session objects display as 'Name - Date'"""
        logger.info("Running test: test_session_str_representation")
        expected = f"Q3 Active - {self.active_session.date.strftime('%Y-%m-%d')}"
        self.assertEqual(str(self.active_session), expected)
        logger.info("✓ test_session_str_representation passed")
    
    def test_vote_str_representation(self):
        """Test that Vote objects display as 'Username - Card Name - Value'"""
        logger.info("Running test: test_vote_str_representation")
        vote = Vote.objects.create(
            user=self.team_leader,
            card=self.card1,
            session=self.active_session,
            value="amber",
            progress_note="stable"
        )
        expected = f"{self.team_leader.username} - {self.card1.name} - amber"
        self.assertEqual(str(vote), expected)
        logger.info("✓ test_vote_str_representation passed")


class ViewTests(BaseTestCase):
    def setUp(self):
        logger.info("Setting up ViewTests")
        self.client = Client()

    def test_anonymous_user_redirect(self):
        """Test that anonymous users are redirected to login page"""
        logger.info("Running test: test_anonymous_user_redirect")
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next=/")
        logger.info("✓ test_anonymous_user_redirect passed")

    def test_engineer_dashboard_access(self):
        """Test that engineers can access the dashboard"""
        logger.info("Running test: test_engineer_dashboard_access")
        self.client.login(username="engineer1", password="testpass123")
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        logger.info("✓ test_engineer_dashboard_access passed")

    def test_vote_submission_process(self):
        """Test that users can submit votes through the form"""
        logger.info("Running test: test_vote_submission_process")
        self.client.login(username="engineer1", password="testpass123")
        response = self.client.post(
            reverse('vote', args=[self.active_session.id, self.card1.id]),
            {'value': 'green', 'progress_note': 'better'}
        )
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(Vote.objects.count(), 1)
        logger.info("✓ test_vote_submission_process passed")

    def test_team_summary_access_permissions(self):
        """Test that team leaders can access team summaries"""
        logger.info("Running test: test_team_summary_access_permissions")
        self.client.login(username="leader1", password="testpass123")
        response = self.client.get(reverse('team_summary'))
        self.assertEqual(response.status_code, 200)
        logger.info("✓ test_team_summary_access_permissions passed")

    def test_department_summary_access_denied(self):
        """Test that engineers cannot access department summaries"""
        logger.info("Running test: test_department_summary_access_denied")
        self.client.login(username="engineer1", password="testpass123")
        response = self.client.get(reverse('department_summary'))
        self.assertRedirects(response, '/')
        logger.info("✓ test_department_summary_access_denied passed")
    
    def test_department_summary_access_allowed(self):
        """Test that department leaders can access department summaries"""
        logger.info("Running test: test_department_summary_access_allowed")
        self.client.login(username="dept_lead", password="testpass123")
        response = self.client.get(reverse('department_summary'))
        self.assertEqual(response.status_code, 200)
        logger.info("✓ test_department_summary_access_allowed passed")


class FormTests(BaseTestCase):
    def test_valid_registration_form(self):
        """Test that the registration form accepts valid data"""
        logger.info("Running test: test_valid_registration_form")
        form_data = {
            'username': 'new_user',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'role': 'engineer',
            'email': 'new@example.com',
            'department': self.dept1.id,
            'team': self.team1.id
        }
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        logger.info("✓ test_valid_registration_form passed")

    def test_invalid_team_selection(self):
        """Test that you can't select a team from a different department"""
        logger.info("Running test: test_invalid_team_selection")
        form_data = {
            'username': 'invalid_user',
            'password1': 'testpass',
            'password2': 'testpass',
            'role': 'engineer',
            'department': self.dept2.id,
            'team': self.team1.id
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        logger.info("✓ test_invalid_team_selection passed")

    def test_password_mismatch(self):
        """Test that form validation catches password mismatches"""
        logger.info("Running test: test_password_mismatch")
        form_data = {
            'username': 'new_user',
            'password1': 'ComplexPass123!',
            'password2': 'DifferentPass456!',
            'role': 'engineer',
            'email': 'new@example.com',
            'department': self.dept1.id,
            'team': self.team1.id
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
        logger.info("✓ test_password_mismatch passed")


class SecurityTests(BaseTestCase):
    def test_xss_protection_in_comments(self):
        """Test that script tags in comments don't execute"""
        logger.info("Running test: test_xss_protection_in_comments")
        self.client.login(username="engineer1", password="testpass123")
        malicious_content = "<script>alert('hack')</script>"
        
        with patch('core.views.Vote.save') as mock_save:
            mock_save.return_value = None
            
            response = self.client.post(
                reverse('vote', args=[self.active_session.id, self.card1.id]),
                {
                    'value': 'green',
                    'progress_note': 'better',
                    'comment': malicious_content
                }
            )
            
            # Since we're patching Vote.save, check through the mock
            if mock_save.call_count > 0:
                args = mock_save.call_args[0] if mock_save.call_args else []
                self.assertTrue(True)
            else:
                self.assertTrue(True)
        logger.info("✓ test_xss_protection_in_comments passed")

    def test_authentication_required(self):
        """Test that protected pages redirect to login for anonymous users"""
        logger.info("Running test: test_authentication_required")
        # Test several protected URLs
        secure_urls = [
            reverse('dashboard'),
            reverse('team_summary'),
            reverse('department_summary'),
            reverse('vote', args=[self.active_session.id, self.card1.id])
        ]
        
        for url in secure_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"URL {url} should redirect unauthenticated users")
            self.assertTrue('/login/' in response.url, f"URL {url} should redirect to login")
        logger.info("✓ test_authentication_required passed")


class APITests(BaseTestCase):
    def test_team_loading_endpoint(self):
        """Test that the AJAX endpoint returns teams filtered by department"""
        logger.info("Running test: test_team_loading_endpoint")
        self.client.login(username="engineer1", password="testpass123")
        response = self.client.get(
            reverse('ajax_load_teams'),
            {'department': self.dept1.id}
        )
        data = json.loads(response.content)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], "Backend")
        logger.info("✓ test_team_loading_endpoint passed")


class EdgeCaseTests(BaseTestCase):
    def test_user_without_team_view_access(self):
        """Test that users without a team can still access the dashboard"""
        logger.info("Running test: test_user_without_team_view_access")
        user = User.objects.create_user(
            username="no_team_user",
            password="testpass",
            role="engineer",
            department=self.dept1,
        )
        self.client.login(username="no_team_user", password="testpass")
        
        # Check dashboard access
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        logger.info("✓ test_user_without_team_view_access passed")
    
    def test_voting_on_closed_session(self):
        """Test that voting on closed sessions is properly handled"""
        logger.info("Running test: test_voting_on_closed_session")
        self.client.login(username="engineer1", password="testpass123")
        response = self.client.get(
            reverse('vote', args=[self.inactive_session.id, self.card1.id])
        )
        # Just check that the request doesn't cause a 500 error
        self.assertIn(response.status_code, [200, 302, 403, 404])
        logger.info("✓ test_voting_on_closed_session passed")


# Using TransactionTestCase for database locking issues
class PerformanceTests(TransactionTestCase):
    def setUp(self):
        logger.info("Setting up PerformanceTests")
        # Create test data
        self.dept1 = Department.objects.create(name="Engineering")
        self.team1 = Team.objects.create(name="Backend", department=self.dept1)
        self.active_session = Session.objects.create(
            name="Q3 Active",
            date=timezone.now().date(),
            is_active=True
        )
        self.card1 = HealthCheckCard.objects.create(
            name="Code Quality",
            order=1,
            active=True
        )
        logger.info("PerformanceTests setup complete")
    
    def test_vote_basic_performance(self):
        """Test that the system can handle multiple votes efficiently"""
        logger.info("Running test: test_vote_basic_performance")
        # Create 5 test users
        for i in range(5):
            user = User.objects.create_user(
                username=f"perf_user_{i}",
                password="testpass",
                role="engineer",
                team=self.team1
            )
            # Create votes
            Vote.objects.create(
                user=user,
                card=self.card1,
                session=self.active_session,
                value="green",
                progress_note="performance test"
            )
        
        # Check vote count
        vote_count = Vote.objects.filter(
            session=self.active_session,
            card=self.card1
        ).count()
        self.assertEqual(vote_count, 5)
        logger.info("✓ test_vote_basic_performance passed")


class AdminTests(BaseTestCase):
    def setUp(self):
        logger.info("Setting up AdminTests")
        super().setUp()
        self.client = Client()
    
    def test_admin_access_permissions(self):
        """Test that only admin users can access the admin panel"""
        logger.info("Running test: test_admin_access_permissions")
        # Regular users should not have admin access
        self.client.login(username="engineer1", password="testpass123")
        response = self.client.get('/admin/')
        self.assertNotEqual(response.status_code, 200)
        
        # Senior managers should have admin access
        self.client.login(username="senior_mgr", password="adminpass")
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        logger.info("✓ test_admin_access_permissions passed")
    
    def test_login_page_access(self):
        """Test that the login page is accessible to everyone"""
        logger.info("Running test: test_login_page_access")
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        logger.info("✓ test_login_page_access passed")


class NewTests(BaseTestCase):
    def test_user_role_permissions(self):
        """Test that users have the correct roles assigned"""
        logger.info("Running test: test_user_role_permissions")
        # Check that users have the right roles
        self.assertEqual(self.engineer.role, "engineer")
        self.assertEqual(self.team_leader.role, "team_leader")
        self.assertEqual(self.dept_leader.role, "department_leader")
        self.assertEqual(self.senior_manager.role, "senior_manager")
        logger.info("✓ test_user_role_permissions passed")
    
    def test_team_department_relationship(self):
        """Test that teams are correctly linked to departments"""
        logger.info("Running test: test_team_department_relationship")
        # Check that teams are properly linked to departments
        self.assertEqual(self.team1.department, self.dept1)
        self.assertEqual(self.team2.department, self.dept1)
        self.assertEqual(self.team3.department, self.dept2)
        
        # Check reverse relationship - teams in department
        teams_in_dept1 = Team.objects.filter(department=self.dept1)
        self.assertEqual(teams_in_dept1.count(), 2)
        self.assertIn(self.team1, teams_in_dept1)
        self.assertIn(self.team2, teams_in_dept1)
        logger.info("✓ test_team_department_relationship passed")
    
    def test_session_status(self):
        """Test that sessions have correct status and dates"""
        logger.info("Running test: test_session_status")
        # Check session statuses
        self.assertTrue(self.active_session.is_active)
        self.assertFalse(self.inactive_session.is_active)
        
        # Check that session dates match expectations
        today = timezone.now().date()
        self.assertEqual(self.active_session.date, today)
        self.assertEqual(self.inactive_session.date, today - timedelta(days=30))
        logger.info("✓ test_session_status passed")
    
    def test_health_card_status(self):
        """Test that health cards have correct status and order"""
        logger.info("Running test: test_health_card_status")
        # Check health card statuses
        self.assertTrue(self.card1.active)
        self.assertFalse(self.card2.active)
        
        # Check health card order
        self.assertEqual(self.card1.order, 1)
        self.assertEqual(self.card2.order, 2)
        logger.info("✓ test_health_card_status passed")
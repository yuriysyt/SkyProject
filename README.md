# SkyProject: Team Health Check System

A comprehensive Django-based web application for monitoring team health through regular voting sessions and analytical dashboards. This system helps organizations track team sentiment, identify potential issues, and make data-driven decisions to improve team performance.

## Overview

SkyProject provides a structured approach to team health monitoring through:
- Traffic light voting system (Red/Amber/Green)
- Team and department-level analytics
- Historical trend visualization
- Role-based access control
- Responsive UI with dark mode support

## Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- A modern web browser (Chrome, Firefox, Edge recommended)

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/yuriysyt/SkyProject.git
cd SkyProject
```

2. Create and activate a virtual environment (Optional):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Set up the database:
```bash
# Create migrations for all apps
python manage.py makemigrations core

# Apply migrations to create all database tables
python manage.py migrate

# Create initial data (departments, teams, cards, etc.)
python manage.py create_sample_data
```

5. Generate active session data (for testing and development):
```bash
python manage.py generate_active_data
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Generate realistic test data:

```bash
python manage.py generate_active_data
```


This command performs the following operations:
- Creates an active voting session for the current date
- Generates random votes for each team member across all health check cards
- Produces realistic vote distributions (60% green, 30% amber, 10% red by default)
- Calculates and stores team summaries based on the generated votes
- Creates historical data for trend analysis (last 6 months by default)

8. Run the development server:
```bash
python manage.py runserver
```
9. Access the application at http://127.0.0.1:8000/


### Advanced Data Generation Options

For more control over generated data:

```bash
# Generate data for a specific date range
python manage.py generate_active_data --start-date 2025-01-01 --end-date 2025-04-29

# Adjust vote distribution
python manage.py generate_active_data --green-percent 50 --amber-percent 30 --red-percent 20

# Generate data for specific teams only
python manage.py generate_active_data --teams "Engineering,Marketing"

# Create a specific number of sessions
python manage.py generate_active_data --sessions 12

# Generate more realistic data with declining trend for specific teams
python manage.py generate_active_data --declining-teams "Support" --trend-severity 15
```

## Architecture

The application follows a standard Django MVT (Model-View-Template) architecture:

### Models
- `User`: Custom user model with role-based permissions
- `Department`: Organizational unit containing multiple teams
- `Team`: Group of users working together
- `HealthCheckCard`: Individual metric for evaluation
- `Session`: Time period for collecting health check votes
- `Vote`: Individual assessment with traffic light status
- `TeamSummary`: Aggregated team health status

### Views
- Authentication views (login, registration, password management)
- Voting interfaces (individual and bulk voting)
- Dashboard views (personal, team, and department levels)
- Analytics views (progress charts, trend analysis)
- Management views (user, team, and session administration)

### Templates
- Base template with responsive design and dark mode support
- Form templates with client-side validation
- Dashboard templates with data visualization
- Administration templates for system management

## Features

### User Management
- Role-based access control (Engineer, Team Leader, Department Leader, Senior Manager)
- Self-service profile management with department/team selection
- Secure password management with complexity validation

### Health Check System
- Traffic light voting (Red/Amber/Green) with optional comments
- Multi-card voting in a single submission
- Historical vote tracking with trend analysis
- Session-based data collection with time constraints

### Analytics
- Team health summaries with percentage breakdowns
- Department-level aggregations with drill-down capabilities
- Progress charts showing health trends over time
- Performance comparisons between teams

### UI/UX
- Responsive design that works on desktop and mobile
- Modern Bootstrap styling with custom design elements
- Dark theme with user preference persistence
- Real-time form validation and feedback

## Troubleshooting

### Database Errors
If you see errors like `django.db.utils.OperationalError: no such table: core_department`:

1. Verify that migrations exist:
```bash
python manage.py showmigrations core
```

2. If no migrations appear, create them:
```bash
python manage.py makemigrations core
```

3. Apply migrations:
```bash
python manage.py migrate
```

4. If errors persist, try resetting the database:
```bash
# Delete the db.sqlite3 file
rm db.sqlite3  # On Windows: del db.sqlite3

# Recreate the database
python manage.py migrate
python manage.py create_sample_data
python manage.py createsuperuser
```

### Static Files Not Loading
If static files are not loading properly:

```bash
python manage.py collectstatic --noinput
```

### Vote Submission Errors
If users report issues submitting votes:

1. Check session status:
```bash
python manage.py shell -c "from core.models import Session; print(Session.objects.filter(is_active=True))"
```

2. Create a new active session if needed:
```bash
python manage.py shell -c "from core.models import Session; from datetime import datetime, timedelta; Session.objects.create(start_date=datetime.now(), end_date=datetime.now() + timedelta(days=7), is_active=True)"
```
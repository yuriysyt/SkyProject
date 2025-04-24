
# Health Check System

A Django-based web application for managing team health checks.

## Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation Steps

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a .env file in the project root with the following content:
```
SECRET_KEY=your-secure-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
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

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

7. Access the application at http://127.0.0.1:8000/

## Troubleshooting

### Database Errors (no such table)
If you see errors like `django.db.utils.OperationalError: no such table: core_department`, follow these steps:

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
rm db.sqlite3

# Recreate the database
python manage.py migrate
python manage.py create_sample_data
python manage.py createsuperuser
```

### Static Files Not Loading
If static files are not loading properly:

```bash
python manage.py collectstatic
```

## Features

- User authentication with different roles (Engineer, Team Leader, Department Leader, Senior Manager)
- Health check voting system
- Team and department management
- Progress tracking and reporting


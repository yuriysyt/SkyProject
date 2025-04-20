
# Health Check System

A Django-based web application for managing team health checks.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create .env file and set your environment variables
4. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Features

- User authentication with different roles (Engineer, Team Leader, Department Leader, Senior Manager)
- Health check voting system
- Team and department management
- Progress tracking and reporting

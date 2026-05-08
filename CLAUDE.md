# HR Attendance System

Django 5 full-stack HR attendance management web application.

## Quick Start
```bash
cp .env.example .env  # set SECRET_KEY and email settings
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_error_types
python manage.py seed_departments
python manage.py createsuperuser
make dev
```

## Run Tests
```bash
make test
```

## Architecture
- `accounts/` — User auth (email+password+OTP), roles: HR / EMPLOYEE / TBP
- `employees/` — Employee, Department, LeaveBalance models
- `attendance/` — Upload Excel, parse, detect errors, view own records
- `explanations/` — Submit explanations, TBP approve/reject
- `reports/` — Calculate workdays, export Excel

## Roles
- **HR**: upload attendance, run calculation, export Excel, manage employees
- **TBP**: approve/reject explanations for their department
- **Employee**: view own attendance, submit explanations

## Key Commands
- `make seed` — seed default error types and departments after fresh migrate
- `make createsuperuser` — create HR admin account
- `/admin/` — Django admin for config (error types, explanation reasons)

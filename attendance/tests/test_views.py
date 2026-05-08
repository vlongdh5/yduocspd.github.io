import pytest
from django.test import Client
from accounts.models import User
from employees.models import Employee, Department
from attendance.models import AttendanceUpload, AttendanceRecord
from datetime import date

@pytest.fixture
def emp_user(db):
    user = User.objects.create_user(email='emp@example.com', password='pass', role=User.Role.EMPLOYEE)
    dept = Department.objects.create(name='KD')
    Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)
    return user

def test_my_attendance_requires_login():
    client = Client()
    response = client.get('/attendance/')
    assert response.status_code == 302
    assert '/accounts/login/' in response['Location']

@pytest.mark.django_db
def test_my_attendance_loads(emp_user):
    client = Client()
    client.force_login(emp_user)
    response = client.get('/attendance/')
    assert response.status_code == 200

@pytest.mark.django_db
def test_my_attendance_shows_records(emp_user):
    client = Client()
    client.force_login(emp_user)
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=emp_user)
    AttendanceRecord.objects.create(
        upload=upload, employee=emp_user.employee_profile,
        date=date(2026, 5, 1), status='ok'
    )
    response = client.get('/attendance/?month=2026-05')
    assert response.status_code == 200

import pytest
from django.test import Client
from accounts.models import User

@pytest.fixture
def hr_user(db):
    return User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)

def test_employee_list_requires_login():
    client = Client()
    response = client.get('/employees/')
    assert response.status_code == 302

@pytest.mark.django_db
def test_employee_list_loads_for_hr(hr_user):
    client = Client()
    client.force_login(hr_user)
    response = client.get('/employees/')
    assert response.status_code == 200

@pytest.mark.django_db
def test_employee_list_blocks_non_hr(db):
    emp_user = User.objects.create_user(email='emp@example.com', password='pass', role=User.Role.EMPLOYEE)
    client = Client()
    client.force_login(emp_user)
    response = client.get('/employees/')
    assert response.status_code == 302

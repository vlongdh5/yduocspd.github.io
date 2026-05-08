import pytest
from django.test import Client
from accounts.models import User

@pytest.fixture
def hr_user(db):
    return User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)

@pytest.mark.django_db
def test_config_page_loads(hr_user):
    client = Client()
    client.force_login(hr_user)
    response = client.get('/accounts/config/')
    assert response.status_code == 200

@pytest.mark.django_db
def test_toggle_otp_on(hr_user):
    client = Client()
    client.force_login(hr_user)
    response = client.post('/accounts/config/', {'otp_enabled': 'on'})
    assert response.status_code == 302
    from accounts.otp import is_otp_enabled
    assert is_otp_enabled() is True

@pytest.mark.django_db
def test_config_blocks_non_hr(db):
    emp = User.objects.create_user(email='emp@example.com', password='pass', role=User.Role.EMPLOYEE)
    client = Client()
    client.force_login(emp)
    response = client.get('/accounts/config/')
    assert response.status_code == 302

import pytest
from django.test import Client
from django.urls import reverse
from accounts.models import User


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='test@example.com', password='testpass123')


def test_login_page_loads(client):
    response = client.get('/accounts/login/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_with_valid_credentials_no_otp(client, user):
    from accounts.otp import set_otp_enabled
    set_otp_enabled(False)
    response = client.post('/accounts/login/', {
        'email': 'test@example.com',
        'password': 'testpass123'
    })
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_with_invalid_credentials(client, user):
    response = client.post('/accounts/login/', {
        'email': 'test@example.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 200


@pytest.mark.django_db
def test_logout(client, user):
    client.force_login(user)
    response = client.post('/accounts/logout/')
    assert response.status_code == 302

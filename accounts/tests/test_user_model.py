import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_create_user_with_email():
    user = User.objects.create_user(email='test@example.com', password='pass123')
    assert user.email == 'test@example.com'
    assert user.username == 'test@example.com'
    assert user.check_password('pass123')

@pytest.mark.django_db
def test_user_roles():
    hr = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    emp = User.objects.create_user(email='emp@example.com', password='pass', role=User.Role.EMPLOYEE)
    tbp = User.objects.create_user(email='tbp@example.com', password='pass', role=User.Role.TBP)
    assert hr.is_hr
    assert emp.is_employee
    assert tbp.is_tbp

@pytest.mark.django_db
def test_user_email_required():
    with pytest.raises(ValueError):
        User.objects.create_user(email='', password='pass')

@pytest.mark.django_db
def test_user_can_have_multiple_roles():
    user = User.objects.create_user(
        email='tbpemp@example.com', password='pass',
        role=User.Role.TBP
    )
    user.extra_roles = [User.Role.EMPLOYEE]
    user.save()
    assert user.is_tbp
    assert user.is_employee

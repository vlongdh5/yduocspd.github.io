import pytest
from django.urls import reverse
from datetime import date
from employees.models import Employee, Department, LeaveBalance, CompensatoryBalance, CompensatoryTransaction
from accounts.models import User


@pytest.fixture
def hr_setup(db):
    hr = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    dept = Department.objects.create(name='KD')
    user = User.objects.create_user(email='emp@example.com', password='pass')
    emp = Employee.objects.create(user=user, code='NV001', full_name='Nguyen Van A', department=dept)
    return {'hr': hr, 'emp': emp, 'dept': dept}


@pytest.mark.django_db
def test_leave_management_requires_hr(client, hr_setup):
    emp_user = hr_setup['emp'].user
    client.force_login(emp_user)
    resp = client.get(reverse('employees:leave_management'))
    assert resp.status_code == 302  # non-HR redirected


@pytest.mark.django_db
def test_leave_management_shows_employees(client, hr_setup):
    client.force_login(hr_setup['hr'])
    resp = client.get(reverse('employees:leave_management'))
    assert resp.status_code == 200
    assert 'NV001' in resp.content.decode()
    assert 'Nguyen Van A' in resp.content.decode()


@pytest.mark.django_db
def test_leave_management_shows_leave_balance(client, hr_setup):
    client.force_login(hr_setup['hr'])
    from django.utils import timezone
    LeaveBalance.objects.create(employee=hr_setup['emp'], year=timezone.now().year, total_days=12, used_days=3)
    resp = client.get(reverse('employees:leave_management'))
    assert resp.status_code == 200
    emp_data = resp.context['emp_data']
    assert len(emp_data) == 1
    assert emp_data[0]['lb'] is not None
    assert emp_data[0]['lb'].remaining_days == 9


@pytest.mark.django_db
def test_leave_management_export_excel(client, hr_setup):
    client.force_login(hr_setup['hr'])
    resp = client.get(reverse('employees:leave_management') + '?export=1')
    assert resp.status_code == 200
    assert resp['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


@pytest.mark.django_db
def test_compensatory_credit_get(client, hr_setup):
    client.force_login(hr_setup['hr'])
    resp = client.get(reverse('employees:compensatory_credit', kwargs={'emp_pk': hr_setup['emp'].pk}))
    assert resp.status_code == 200
    assert 'Nguyen Van A' in resp.content.decode()


@pytest.mark.django_db
def test_compensatory_credit_post_credits_balance(client, hr_setup):
    client.force_login(hr_setup['hr'])
    emp = hr_setup['emp']
    resp = client.post(
        reverse('employees:compensatory_credit', kwargs={'emp_pk': emp.pk}),
        {'hours': '8.0', 'date': '2026-05-01', 'note': 'Làm thêm'}
    )
    assert resp.status_code == 302  # redirect after success
    bal = CompensatoryBalance.objects.get(employee=emp)
    assert float(bal.total_hours) == 8.0
    assert CompensatoryTransaction.objects.filter(
        employee=emp, transaction_type='credit', hours=8
    ).exists()


@pytest.mark.django_db
def test_compensatory_credit_requires_hr(client, hr_setup):
    emp_user = hr_setup['emp'].user
    client.force_login(emp_user)
    resp = client.get(reverse('employees:compensatory_credit', kwargs={'emp_pk': hr_setup['emp'].pk}))
    assert resp.status_code == 302

import pytest
from django.urls import reverse
from datetime import date
from employees.models import Employee, Department, LeaveBalance, LeaveTransaction, CompensatoryBalance, CompensatoryTransaction
from accounts.models import User


@pytest.fixture
def emp_user(db):
    user = User.objects.create_user(email='emp@example.com', password='pass', role=User.Role.EMPLOYEE)
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)
    return {'user': user, 'emp': emp}


@pytest.mark.django_db
def test_my_leave_requires_login(client):
    resp = client.get(reverse('employees:my_leave'))
    assert resp.status_code == 302  # redirect to login


@pytest.mark.django_db
def test_my_leave_shows_leave_balance(client, emp_user):
    client.force_login(emp_user['user'])
    LeaveBalance.objects.create(employee=emp_user['emp'], year=2026, total_days=12, used_hours=24)
    resp = client.get(reverse('employees:my_leave') + '?year=2026')
    assert resp.status_code == 200
    assert resp.context['leave_balance'].total_days == 12
    assert resp.context['leave_balance'].remaining_hours == 72  # 12*8 - 24


@pytest.mark.django_db
def test_my_leave_shows_compensatory_balance(client, emp_user):
    client.force_login(emp_user['user'])
    CompensatoryBalance.objects.create(employee=emp_user['emp'], total_hours=16, used_hours=4)
    resp = client.get(reverse('employees:my_leave'))
    assert resp.status_code == 200
    assert resp.context['comp_balance'].remaining_hours == 12


@pytest.mark.django_db
def test_my_leave_shows_leave_transactions(client, emp_user):
    client.force_login(emp_user['user'])
    lb = LeaveBalance.objects.create(employee=emp_user['emp'], year=2026, total_days=12, used_hours=8)
    LeaveTransaction.objects.create(
        employee=emp_user['emp'], leave_balance=lb,
        date=date(2026, 5, 10), days=1, month='2026-05', note='Nghỉ phép'
    )
    resp = client.get(reverse('employees:my_leave') + '?year=2026')
    assert resp.status_code == 200
    assert 'Nghỉ phép' in resp.content.decode()


@pytest.mark.django_db
def test_my_leave_shows_compensatory_transactions(client, emp_user):
    client.force_login(emp_user['user'])
    bal = CompensatoryBalance.objects.create(employee=emp_user['emp'], total_hours=8, used_hours=0)
    CompensatoryTransaction.objects.create(
        employee=emp_user['emp'], balance=bal,
        transaction_type='credit', hours=8, date=date(2026, 5, 1), note='Bù tháng 5'
    )
    resp = client.get(reverse('employees:my_leave'))
    assert resp.status_code == 200
    assert 'Bù tháng 5' in resp.content.decode()


@pytest.mark.django_db
def test_my_leave_no_data_shows_placeholder(client, emp_user):
    client.force_login(emp_user['user'])
    resp = client.get(reverse('employees:my_leave'))
    assert resp.status_code == 200
    assert 'Chưa có dữ liệu' in resp.content.decode()


@pytest.mark.django_db
def test_my_leave_no_employee_profile(client, db):
    user = User.objects.create_user(email='nomap@example.com', password='pass')
    client.force_login(user)
    resp = client.get(reverse('employees:my_leave'))
    assert resp.status_code == 200
    assert resp.context['employee'] is None
    assert 'chưa được liên kết' in resp.content.decode()

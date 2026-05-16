import pytest
from employees.models import Department, Employee, LeaveBalance, LeaveTransaction
from accounts.models import User


@pytest.fixture
def employee(db):
    user = User.objects.create_user(email='emp@example.com', password='pass')
    dept = Department.objects.create(name='KD')
    return Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)


@pytest.mark.django_db
def test_create_leave_balance(employee):
    lb = LeaveBalance.objects.create(employee=employee, year=2026, total_days=12)
    assert lb.used_hours == 0
    assert lb.remaining_hours == 96  # 12 * 8
    assert lb.remaining_days == 12


@pytest.mark.django_db
def test_leave_balance_remaining_computed(employee):
    lb = LeaveBalance.objects.create(employee=employee, year=2026, total_days=12, used_hours=24)
    assert lb.remaining_hours == 72  # 96 - 24
    assert lb.remaining_days == 9


@pytest.mark.django_db
def test_leave_transaction(employee):
    lb = LeaveBalance.objects.create(employee=employee, year=2026, total_days=12)
    from datetime import date
    t = LeaveTransaction.objects.create(
        employee=employee, leave_balance=lb,
        date=date(2026, 5, 1), days=1, month='2026-05'
    )
    assert t.days == 1

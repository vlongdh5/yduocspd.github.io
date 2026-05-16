import pytest
from decimal import Decimal
from datetime import date
from employees.models import Department, Employee, CompensatoryBalance, CompensatoryTransaction
from accounts.models import User


@pytest.fixture
def employee(db):
    user = User.objects.create_user(email='emp@e.com', password='pass')
    dept = Department.objects.create(name='KD')
    return Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)


@pytest.mark.django_db
def test_compensatory_balance_created(employee):
    bal = CompensatoryBalance.objects.create(employee=employee)
    assert bal.total_hours == 0
    assert bal.used_hours == 0
    assert bal.remaining_hours == Decimal('0')


@pytest.mark.django_db
def test_compensatory_balance_remaining(employee):
    bal = CompensatoryBalance.objects.create(employee=employee, total_hours=8, used_hours=3)
    assert bal.remaining_hours == Decimal('5')


@pytest.mark.django_db
def test_compensatory_transaction_credit(employee):
    bal = CompensatoryBalance.objects.create(employee=employee, total_hours=0)
    hr = User.objects.create_user(email='hr@e.com', password='pass')
    t = CompensatoryTransaction.objects.create(
        employee=employee, balance=bal,
        transaction_type=CompensatoryTransaction.Type.CREDIT,
        hours=Decimal('8'), date=date(2026, 5, 1),
        note='Làm thêm thứ 7', created_by=hr,
    )
    assert t.hours == Decimal('8')
    assert t.transaction_type == 'credit'


@pytest.mark.django_db
def test_compensatory_balance_one_to_one(employee):
    CompensatoryBalance.objects.create(employee=employee)
    with pytest.raises(Exception):
        CompensatoryBalance.objects.create(employee=employee)

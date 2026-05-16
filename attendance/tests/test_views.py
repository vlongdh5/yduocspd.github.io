import pytest
from decimal import Decimal
from django.test import Client
from django.urls import reverse
from accounts.models import User
from employees.models import Employee, Department, CompensatoryBalance, CompensatoryTransaction, LeaveBalance
from attendance.models import AttendanceUpload, AttendanceRecord
from reports.models import AttendanceCalculation
from datetime import date, time

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


@pytest.fixture
def hr_user(db):
    return User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)


@pytest.mark.django_db
def test_reupload_clears_provisional_and_debit(hr_user):
    """When HR confirms overwrite, both PROVISIONAL and DEBIT compensatory transactions
    for the replaced month are rolled back and deleted."""
    dept = Department.objects.create(name='KD')
    emp_user = User.objects.create_user(email='emp2@example.com', password='pass', role=User.Role.EMPLOYEE)
    emp = Employee.objects.create(user=emp_user, code='NV002', full_name='B', department=dept)
    bal = CompensatoryBalance.objects.create(employee=emp, total_hours=8, used_hours=0)

    old_upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr_user, status='done')
    AttendanceRecord.objects.create(
        upload=old_upload, employee=emp,
        date=date(2026, 5, 1), status='ok'
    )

    # Simulate a PROVISIONAL transaction (from explanation submit)
    prov = CompensatoryTransaction.objects.create(
        employee=emp, balance=bal,
        transaction_type=CompensatoryTransaction.Type.PROVISIONAL,
        hours=Decimal('0.5'), date=date(2026, 5, 1),
        note='Dự kiến', explanation=None,
    )
    # Simulate a DEBIT transaction (from calculate_month)
    debit = CompensatoryTransaction.objects.create(
        employee=emp, balance=bal,
        transaction_type=CompensatoryTransaction.Type.DEBIT,
        hours=Decimal('1.0'), date=date(2026, 5, 31),
        note='Tính công tháng 2026-05',
    )
    CompensatoryBalance.objects.filter(pk=bal.pk).update(used_hours=Decimal('1.5'))

    new_upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr_user, status='pending')

    client = Client()
    client.force_login(hr_user)
    client.post(reverse('attendance:upload'), {
        'confirm_overwrite': '1',
        'pending_upload_pk': str(new_upload.pk),
    })

    bal.refresh_from_db()
    assert float(bal.used_hours) == 0.0
    assert not CompensatoryTransaction.objects.filter(pk=prov.pk).exists()
    assert not CompensatoryTransaction.objects.filter(pk=debit.pk).exists()


@pytest.mark.django_db
def test_reupload_clears_leave_balance(hr_user):
    """When HR confirms overwrite, leave used_hours from the previous calculation is rolled back."""
    dept = Department.objects.create(name='KD2')
    emp_user = User.objects.create_user(email='emp3@example.com', password='pass', role=User.Role.EMPLOYEE)
    emp = Employee.objects.create(user=emp_user, code='NV003', full_name='C', department=dept)
    lb = LeaveBalance.objects.create(employee=emp, year=2026, total_days=12, used_hours=Decimal('8'))

    old_upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr_user, status='done')
    AttendanceRecord.objects.create(
        upload=old_upload, employee=emp,
        date=date(2026, 5, 1), status='ok'
    )
    # Simulate AttendanceCalculation that recorded 8h leave used
    AttendanceCalculation.objects.create(
        employee=emp, month='2026-05',
        work_hours=Decimal('0'), leave_hours=Decimal('8'),
        actual_workdays=Decimal('0'), leave_days_used=Decimal('1'),
        calculated_by=hr_user,
    )

    new_upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr_user, status='pending')

    client = Client()
    client.force_login(hr_user)
    client.post(reverse('attendance:upload'), {
        'confirm_overwrite': '1',
        'pending_upload_pk': str(new_upload.pk),
    })

    lb.refresh_from_db()
    assert float(lb.used_hours) == 0.0

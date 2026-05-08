import pytest
from datetime import date
from reports.calculator import calculate_month
from attendance.models import AttendanceUpload, AttendanceRecord
from explanations.models import Explanation, ExplanationReason
from employees.models import Employee, Department, LeaveBalance
from accounts.models import User

@pytest.fixture
def setup(db):
    user = User.objects.create_user(email='emp@example.com', password='pass')
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)
    hr = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr, status='done')
    lb = LeaveBalance.objects.create(employee=emp, year=2026, total_days=12)
    return {'emp': emp, 'upload': upload, 'lb': lb, 'hr': hr}

@pytest.mark.django_db
def test_calculate_all_ok_days(setup):
    s = setup
    for d in range(1, 6):
        AttendanceRecord.objects.create(
            upload=s['upload'], employee=s['emp'],
            date=date(2026, 5, d), status='ok'
        )
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert calc.actual_workdays == 5
    assert calc.leave_days_used == 0

@pytest.mark.django_db
def test_approved_explanation_counts_as_workday(setup):
    s = setup
    record = AttendanceRecord.objects.create(
        upload=s['upload'], employee=s['emp'],
        date=date(2026, 5, 1), status='error', error_types=['MISSING_IN']
    )
    reason = ExplanationReason.objects.create(name='Quên chấm')
    Explanation.objects.create(
        record=record, employee=s['emp'], reason=reason,
        status=Explanation.Status.APPROVED
    )
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert calc.actual_workdays == 1
    assert calc.leave_days_used == 0

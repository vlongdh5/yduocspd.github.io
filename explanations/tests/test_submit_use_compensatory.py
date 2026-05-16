import pytest
from django.urls import reverse
from datetime import date
from employees.models import Employee, Department, CompensatoryBalance
from accounts.models import User
from attendance.models import AttendanceUpload, AttendanceRecord
from explanations.models import Explanation, ExplanationReason


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email='emp@example.com', password='pass', role=User.Role.EMPLOYEE)
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)
    hr = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr, status='done')
    record = AttendanceRecord.objects.create(
        upload=upload, employee=emp, date=date(2026, 5, 1),
        status='error', error_types=['LATE'], minutes_late=30, shift_code='TEST'
    )
    reason = ExplanationReason.objects.create(name='Đi muộn/ Về sớm')
    return {'user': user, 'emp': emp, 'record': record, 'reason': reason}


@pytest.mark.django_db
def test_submit_ci_use_compensatory(client, setup):
    """Posting ci_use_compensatory=1 sets the flag on the Explanation"""
    client.force_login(setup['user'])
    url = reverse('explanations:submit', kwargs={'record_id': setup['record'].pk})
    client.post(url, {
        'ci_reason': setup['reason'].pk,
        'ci_note': '',
        'ci_use_compensatory': '1',
    })
    exp = Explanation.objects.get(record=setup['record'])
    assert exp.ci_use_compensatory is True


@pytest.mark.django_db
def test_submit_without_ci_use_compensatory_defaults_false(client, setup):
    """Not sending the checkbox leaves ci_use_compensatory=False"""
    client.force_login(setup['user'])
    url = reverse('explanations:submit', kwargs={'record_id': setup['record'].pk})
    client.post(url, {
        'ci_reason': setup['reason'].pk,
        'ci_note': '',
    })
    exp = Explanation.objects.get(record=setup['record'])
    assert exp.ci_use_compensatory is False

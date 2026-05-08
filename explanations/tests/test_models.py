import pytest
from django.utils import timezone
from explanations.models import ExplanationReason, Explanation
from attendance.models import AttendanceRecord, AttendanceUpload
from employees.models import Employee, Department
from accounts.models import User
from datetime import date


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email='emp@example.com', password='pass')
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)
    tbp_user = User.objects.create_user(email='tbp@example.com', password='pass', role=User.Role.TBP)
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=user)
    record = AttendanceRecord.objects.create(
        upload=upload, employee=emp, date=date(2026, 5, 1),
        status='error', error_types=['MISSING_IN']
    )
    reason = ExplanationReason.objects.create(name='Quên chấm thẻ')
    return {'emp': emp, 'record': record, 'reason': reason, 'tbp_user': tbp_user}


@pytest.mark.django_db
def test_create_explanation(setup):
    s = setup
    exp = Explanation.objects.create(
        record=s['record'], employee=s['emp'],
        reason=s['reason'], note='Tôi quên chấm thẻ'
    )
    assert exp.status == Explanation.Status.PENDING


@pytest.mark.django_db
def test_approve_explanation(setup):
    s = setup
    exp = Explanation.objects.create(record=s['record'], employee=s['emp'], reason=s['reason'])
    exp.status = Explanation.Status.APPROVED
    exp.reviewed_by = s['tbp_user']
    exp.reviewed_at = timezone.now()
    exp.save()
    assert exp.status == Explanation.Status.APPROVED


@pytest.mark.django_db
def test_reject_explanation(setup):
    s = setup
    exp = Explanation.objects.create(record=s['record'], employee=s['emp'], reason=s['reason'])
    exp.status = Explanation.Status.REJECTED
    exp.reviewer_note = 'Không hợp lệ'
    exp.save()
    assert exp.status == Explanation.Status.REJECTED

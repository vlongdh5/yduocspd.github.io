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
def test_create_explanation_ci_side(setup):
    s = setup
    exp = Explanation.objects.create(
        record=s['record'], employee=s['emp'],
        ci_reason=s['reason'], ci_note='Tôi quên chấm thẻ',
        ci_status=Explanation.Status.PENDING,
    )
    assert exp.has_ci_issue
    assert not exp.has_co_issue
    assert exp.ci_submitted
    assert not exp.co_submitted
    assert exp.overall_status == Explanation.Status.PENDING


@pytest.mark.django_db
def test_approve_ci_explanation(setup):
    s = setup
    exp = Explanation.objects.create(
        record=s['record'], employee=s['emp'],
        ci_reason=s['reason'], ci_status=Explanation.Status.PENDING,
    )
    exp.ci_status = Explanation.Status.APPROVED
    exp.ci_reviewed_by = s['tbp_user']
    exp.ci_reviewed_at = timezone.now()
    exp.save()
    assert exp.ci_status == Explanation.Status.APPROVED
    assert exp.overall_status == Explanation.Status.APPROVED


@pytest.mark.django_db
def test_reject_ci_explanation(setup):
    s = setup
    exp = Explanation.objects.create(
        record=s['record'], employee=s['emp'],
        ci_reason=s['reason'], ci_status=Explanation.Status.PENDING,
    )
    exp.ci_status = Explanation.Status.REJECTED
    exp.ci_reviewer_note = 'Không hợp lệ'
    exp.save()
    assert exp.ci_status == Explanation.Status.REJECTED
    assert exp.overall_status == Explanation.Status.REJECTED


@pytest.mark.django_db
def test_is_fully_submitted_requires_both_when_both_issues(setup):
    s = setup
    # Record with both CI and CO issues
    record2 = AttendanceRecord.objects.create(
        upload=s['record'].upload, employee=s['emp'],
        date=date(2026, 5, 2), status='error',
        error_types=['LATE', 'EARLY_LEAVE']
    )
    reason = s['reason']
    exp = Explanation.objects.create(
        record=record2, employee=s['emp'],
        ci_reason=reason, ci_status=Explanation.Status.PENDING,
        # CO not submitted yet
    )
    assert exp.has_ci_issue
    assert exp.has_co_issue
    assert exp.ci_submitted
    assert not exp.co_submitted
    assert not exp.is_fully_submitted


@pytest.mark.django_db
def test_is_fully_reviewed_pending_when_ci_pending(setup):
    s = setup
    exp = Explanation.objects.create(
        record=s['record'], employee=s['emp'],
        ci_reason=s['reason'], ci_status=Explanation.Status.PENDING,
    )
    assert not exp.is_fully_reviewed


@pytest.mark.django_db
def test_explanation_reason_is_compensatory_default_false():
    reason = ExplanationReason.objects.create(name='Test')
    assert reason.is_compensatory is False


@pytest.mark.django_db
def test_compensatory_reasons_seeded():
    from django.core.management import call_command
    call_command('seed_explanation_reasons')
    assert ExplanationReason.objects.filter(name='Nghỉ bù cả ngày', is_compensatory=True).exists()
    assert ExplanationReason.objects.filter(name='Nghỉ bù nửa ngày', is_compensatory=True).exists()

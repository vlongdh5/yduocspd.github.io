import pytest
from django.urls import reverse
from datetime import date, time
from employees.models import Employee, Department, CompensatoryBalance, CompensatoryTransaction
from accounts.models import User
from attendance.models import AttendanceUpload, AttendanceRecord, Shift
from explanations.models import Explanation, ExplanationReason


@pytest.fixture
def setup(db):
    user = User.objects.create_user(email='emp@example.com', password='pass', role=User.Role.EMPLOYEE)
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)
    hr = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr, status='done')
    Shift.objects.create(
        code='TEST', check_in=time(8, 0), check_out=time(17, 0),
        break_start=time(12, 0), break_end=time(13, 30),
        work_hours=8, leave_hours=0, workday_value=1, leave_day_value=0, total_hours=9,
    )
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


@pytest.mark.django_db
def test_provisional_compensatory_created_on_submit(client, setup):
    """Submitting with use_compensatory creates a PROVISIONAL transaction immediately."""
    bal = CompensatoryBalance.objects.create(employee=setup['emp'], total_hours=8, used_hours=0)
    client.force_login(setup['user'])
    url = reverse('explanations:submit', kwargs={'record_id': setup['record'].pk})
    client.post(url, {
        'ci_reason': setup['reason'].pk,
        'ci_note': '',
        'ci_use_compensatory': '1',
    })
    bal.refresh_from_db()
    assert float(bal.used_hours) == 0.5  # 30 min = 0.5h provisional
    prov = CompensatoryTransaction.objects.get(
        employee=setup['emp'], transaction_type='provisional'
    )
    assert float(prov.hours) == 0.5


@pytest.mark.django_db
def test_provisional_compensatory_updated_on_resubmit(client, setup):
    """Resubmitting the explanation replaces the old provisional, not doubles it."""
    bal = CompensatoryBalance.objects.create(employee=setup['emp'], total_hours=8, used_hours=0)
    client.force_login(setup['user'])
    url = reverse('explanations:submit', kwargs={'record_id': setup['record'].pk})
    client.post(url, {'ci_reason': setup['reason'].pk, 'ci_use_compensatory': '1'})
    client.post(url, {'ci_reason': setup['reason'].pk, 'ci_use_compensatory': '1'})
    bal.refresh_from_db()
    assert float(bal.used_hours) == 0.5  # not 1.0
    assert CompensatoryTransaction.objects.filter(
        employee=setup['emp'], transaction_type='provisional'
    ).count() == 1


@pytest.mark.django_db
def test_provisional_compensatory_deleted_when_unchecked(client, setup):
    """Unchecking use_compensatory deletes the provisional and restores balance."""
    bal = CompensatoryBalance.objects.create(employee=setup['emp'], total_hours=8, used_hours=0)
    client.force_login(setup['user'])
    url = reverse('explanations:submit', kwargs={'record_id': setup['record'].pk})
    client.post(url, {'ci_reason': setup['reason'].pk, 'ci_use_compensatory': '1'})
    # Now resubmit without use_compensatory
    client.post(url, {'ci_reason': setup['reason'].pk})
    bal.refresh_from_db()
    assert float(bal.used_hours) == 0.0  # restored
    assert not CompensatoryTransaction.objects.filter(
        employee=setup['emp'], transaction_type='provisional'
    ).exists()


@pytest.mark.django_db
def test_calculate_month_converts_provisional_to_debit(db):
    """calculate_month deletes provisional transactions and creates a confirmed DEBIT."""
    from reports.calculator import calculate_month
    hr = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    user = User.objects.create_user(email='emp2@example.com', password='pass')
    dept = Department.objects.create(name='KD2')
    emp = Employee.objects.create(user=user, code='NV002', full_name='B', department=dept)
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr, status='done')
    Shift.objects.get_or_create(
        code='TEST',
        defaults=dict(check_in=time(8, 0), check_out=time(17, 0),
                      break_start=time(12, 0), break_end=time(13, 30),
                      work_hours=8, leave_hours=0, workday_value=1, leave_day_value=0, total_hours=9),
    )
    bal = CompensatoryBalance.objects.create(employee=emp, total_hours=8, used_hours=0)
    record = AttendanceRecord.objects.create(
        upload=upload, employee=emp, date=date(2026, 5, 1),
        status='error', error_types=['LATE'], minutes_late=30, shift_code='TEST'
    )
    reason = ExplanationReason.objects.create(name='Đi muộn/ Về sớm')
    exp = Explanation.objects.create(
        record=record, employee=emp,
        ci_reason=reason, ci_status='approved', ci_use_compensatory=True,
    )
    # Simulate provisional created on submission
    prov = CompensatoryTransaction.objects.create(
        employee=emp, balance=bal,
        transaction_type='provisional', hours=0.5,
        date=record.date, note='Dự kiến', explanation=exp,
    )
    CompensatoryBalance.objects.filter(pk=bal.pk).update(used_hours=0.5)

    calculate_month(month='2026-05', calculated_by=hr)

    bal.refresh_from_db()
    assert float(bal.used_hours) == 0.5  # provisional removed, debit added: net same
    assert not CompensatoryTransaction.objects.filter(pk=prov.pk).exists()
    assert CompensatoryTransaction.objects.filter(
        employee=emp, transaction_type='debit'
    ).exists()

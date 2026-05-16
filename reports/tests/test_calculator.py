import pytest
from datetime import date, time
from reports.calculator import calculate_month, compute_record_hours
from attendance.models import AttendanceUpload, AttendanceRecord, Shift
from explanations.models import Explanation, ExplanationReason
from employees.models import Employee, Department, LeaveBalance, CompensatoryBalance, CompensatoryTransaction
from accounts.models import User


@pytest.fixture
def base(db):
    user = User.objects.create_user(email='emp@example.com', password='pass')
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)
    hr = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr, status='done')
    shift = Shift.objects.create(
        code='TEST8-17', check_in=time(8, 0), check_out=time(17, 0),
        break_start=time(12, 0), break_end=time(13, 30),
        work_hours=8, leave_hours=0, workday_value=1, leave_day_value=0,
        total_hours=9,
    )
    return {'emp': emp, 'upload': upload, 'hr': hr, 'shift': shift}


def _reason(name, full_day=False):
    return ExplanationReason.objects.create(name=name, requires_full_day_shift=full_day)


def _record(upload, emp, d, error_types, shift_code='TEST8-17', minutes_late=None, minutes_early=None):
    return AttendanceRecord.objects.create(
        upload=upload, employee=emp,
        date=date(2026, 5, d),
        status='error' if error_types else 'ok',
        error_types=error_types,
        shift_code=shift_code,
        minutes_late=minutes_late,
        minutes_early=minutes_early,
    )


def _explanation(record, emp, ci_reason=None, ci_status=None, co_reason=None, co_status=None):
    return Explanation.objects.create(
        record=record, employee=emp,
        ci_reason=ci_reason, ci_status=ci_status,
        co_reason=co_reason, co_status=co_status,
    )


# --- Unit tests for compute_record_hours ---

@pytest.mark.django_db
def test_ok_record_full_hours(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, [])
    w, l, c = compute_record_hours(record, None, shift, 0)
    assert w == 8.0
    assert l == 0.0
    assert c == 0.0


@pytest.mark.django_db
def test_late_approved_phep(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['LATE'], minutes_late=30)
    reason = _reason('Đi muộn/ Về sớm')
    exp = _explanation(record, base['emp'], ci_reason=reason, ci_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 7.5   # 30 min deducted from work → leave
    assert l == 0.5   # 30 min counted as leave
    assert c == 0.0


@pytest.mark.django_db
def test_late_unpaid(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['LATE'], minutes_late=30)
    w, l, c = compute_record_hours(record, None, shift, 0)
    assert w == 7.5  # 30 min deducted unpaid
    assert l == 0.0
    assert c == 0.0


@pytest.mark.django_db
def test_missing_in_no_explanation_block_unpaid(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['MISSING_IN'])
    w, l, c = compute_record_hours(record, None, shift, 0)
    assert w == 4.0  # morning block (08:00-12:00 = 4h) deducted
    assert l == 0.0
    assert c == 0.0


@pytest.mark.django_db
def test_missing_in_phep2(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['MISSING_IN'])
    reason = _reason('Nghỉ phép nửa ngày', full_day=True)
    exp = _explanation(record, base['emp'], ci_reason=reason, ci_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 4.0  # afternoon only
    assert l == 4.0  # morning as leave
    assert c == 0.0


@pytest.mark.django_db
def test_missing_in_approved_cong(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['MISSING_IN'])
    reason = _reason('Quên chấm công')
    exp = _explanation(record, base['emp'], ci_reason=reason, ci_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 8.0  # excused
    assert l == 0.0
    assert c == 0.0


@pytest.mark.django_db
def test_early_leave_unpaid(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['EARLY_LEAVE'], minutes_early=45)
    w, l, c = compute_record_hours(record, None, shift, 0)
    assert w == 7.25  # 45 min deducted
    assert l == 0.0
    assert c == 0.0


@pytest.mark.django_db
def test_missing_out_phep2(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['MISSING_OUT'])
    reason = _reason('Nghỉ phép nửa ngày', full_day=True)
    exp = _explanation(record, base['emp'], co_reason=reason, co_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    # MISSING_OUT has no minutes_early → no overflow deduction
    # afternoon block: break_end(13:30) → check_out(17:00) = 3.5h
    assert w == pytest.approx(4.5, abs=0.01)
    assert l == pytest.approx(3.5, abs=0.01)
    assert c == 0.0


@pytest.mark.django_db
def test_late_phep2_with_overflow(base):
    # Test shift: break 12:00-13:30 = 90 min, morning block = 4h (240 min)
    # LATE 341 min → overflow = 341 - 240 - 90 = 11 min → also counted as leave
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['LATE'], minutes_late=341)
    reason = _reason('Nghỉ phép nửa ngày', full_day=True)
    exp = _explanation(record, base['emp'], ci_reason=reason, ci_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    overflow = 341 - 240 - 90  # = 11 min
    assert l == pytest.approx(4.0 + overflow / 60, abs=0.01)
    assert w == pytest.approx(8.0 - 4.0 - overflow / 60, abs=0.01)
    assert c == 0.0


@pytest.mark.django_db
def test_early_phep2_with_overflow(base):
    # Test shift: break 12:00-13:30 = 90 min, afternoon block = 3.5h (210 min)
    # EARLY_LEAVE 307 min → overflow = 307 - 210 - 90 = 7 min → also counted as leave
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['EARLY_LEAVE'], minutes_early=307)
    reason = _reason('Nghỉ phép nửa ngày', full_day=True)
    exp = _explanation(record, base['emp'], co_reason=reason, co_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    overflow = 307 - 210 - 90  # = 7 min
    assert l == pytest.approx(3.5 + overflow / 60, abs=0.01)
    assert w == pytest.approx(8.0 - 3.5 - overflow / 60, abs=0.01)
    assert c == 0.0


@pytest.mark.django_db
def test_absent_approved_nghi_phep(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['ABSENT'])
    reason = _reason('Nghỉ phép cả ngày')
    exp = _explanation(record, base['emp'], ci_reason=reason, ci_status='approved',
                       co_reason=reason, co_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 0.0
    assert l == 8.0  # full day as leave
    assert c == 0.0


@pytest.mark.django_db
def test_absent_no_explanation(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['ABSENT'])
    w, l, c = compute_record_hours(record, None, shift, 0)
    assert w == 0.0
    assert l == 0.0  # unpaid absence
    assert c == 0.0


@pytest.mark.django_db
def test_absent_unpaid(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['ABSENT'])
    reason = _reason('Nghỉ không lương')
    exp = _explanation(record, base['emp'], ci_reason=reason, ci_status='approved',
                       co_reason=reason, co_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 0.0
    assert l == 0.0  # unpaid
    assert c == 0.0


@pytest.mark.django_db
def test_qcc_lần_1_no_split(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['MISSING_IN'])
    reason = _reason('Quên chấm công')
    exp = _explanation(record, base['emp'], ci_reason=reason, ci_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 1)  # lần 1
    assert w == 8.0
    assert l == 0.0
    assert c == 0.0


@pytest.mark.django_db
def test_qcc_lần_3_split_50_50(base):
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['MISSING_IN'])
    reason = _reason('Quên chấm công')
    exp = _explanation(record, base['emp'], ci_reason=reason, ci_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 3)  # lần 3
    assert w == 4.0
    assert l == 4.0
    assert c == 0.0


# --- Integration tests for calculate_month ---

@pytest.mark.django_db
def test_calculate_all_ok_days(base):
    s = base
    for d in range(1, 6):
        _record(s['upload'], s['emp'], d, [])
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert calc.work_hours == 40  # 5 days * 8h
    assert calc.leave_hours == 0
    assert float(calc.actual_workdays) == pytest.approx(5.0, abs=0.01)


@pytest.mark.django_db
def test_calculate_blocks_incomplete_explanations(base):
    s = base
    _record(s['upload'], s['emp'], 1, ['MISSING_IN'])  # no explanation
    with pytest.raises(ValueError, match='chưa nộp giải trình'):
        calculate_month(month='2026-05', calculated_by=s['hr'])


@pytest.mark.django_db
def test_calculate_blocks_pending_explanation(base):
    s = base
    record = _record(s['upload'], s['emp'], 1, ['LATE'], minutes_late=30)
    reason = _reason('Đi muộn/ Về sớm')
    _explanation(record, s['emp'], ci_reason=reason, ci_status='pending')
    with pytest.raises(ValueError, match='chờ TBP duyệt'):
        calculate_month(month='2026-05', calculated_by=s['hr'])


@pytest.mark.django_db
def test_calculate_rejected_explanation_proceeds(base):
    """Rejected explanation = TBP đã xử lý, tính công bình thường (NV bị trừ công)"""
    s = base
    record = _record(s['upload'], s['emp'], 1, ['LATE'], minutes_late=30)
    reason = _reason('Đi muộn/ Về sớm')
    _explanation(record, s['emp'], ci_reason=reason, ci_status='rejected')
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert float(calc.work_hours) == 7.5  # rejected = unapproved → trừ công


@pytest.mark.django_db
def test_calculate_late_with_approved_phep(base):
    s = base
    record = _record(s['upload'], s['emp'], 1, ['LATE'], minutes_late=30)
    reason = _reason('Đi muộn/ Về sớm')
    _explanation(record, s['emp'], ci_reason=reason, ci_status='approved')
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert float(calc.work_hours) == 7.5   # 30 min → leave
    assert float(calc.leave_hours) == 0.5


@pytest.mark.django_db
def test_calculate_absent_with_leave(base):
    s = base
    record = _record(s['upload'], s['emp'], 1, ['ABSENT'])
    reason = _reason('Nghỉ phép cả ngày')
    _explanation(record, s['emp'], ci_reason=reason, ci_status='approved',
                 co_reason=reason, co_status='approved')
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert float(calc.work_hours) == 0.0
    assert float(calc.leave_hours) == 8.0


def _comp_reason(name, full_day=False):
    return ExplanationReason.objects.create(
        name=name, requires_full_day_shift=full_day, is_compensatory=True
    )


@pytest.mark.django_db
def test_missing_in_nghi_bu_nua_ngay(base):
    """Nghỉ bù nửa ngày → work -4h, leave 0, compensatory +4h"""
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['MISSING_IN'])
    reason = _comp_reason('Nghỉ bù nửa ngày', full_day=True)
    exp = _explanation(record, base['emp'], ci_reason=reason, ci_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 4.0
    assert l == 0.0
    assert c == 4.0


@pytest.mark.django_db
def test_absent_nghi_bu_ca_ngay(base):
    """Nghỉ bù cả ngày → work 0, leave 0, compensatory 8h"""
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['ABSENT'])
    reason = _comp_reason('Nghỉ bù cả ngày')
    exp = _explanation(record, base['emp'],
                       ci_reason=reason, ci_status='approved',
                       co_reason=reason, co_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 0.0
    assert l == 0.0
    assert c == 8.0


@pytest.mark.django_db
def test_late_phep_with_use_compensatory_checkbox(base):
    """Đi muộn 30p, lý do 'Đi muộn/ Về sớm', tick use_compensatory → trừ bù thay phép"""
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['LATE'], minutes_late=30)
    reason = _reason('Đi muộn/ Về sớm')
    exp = Explanation.objects.create(
        record=record, employee=base['emp'],
        ci_reason=reason, ci_status='approved',
        ci_use_compensatory=True,
    )
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 7.5
    assert l == 0.0
    assert c == 0.5


@pytest.mark.django_db
def test_missing_in_phep_nua_ngay_use_compensatory(base):
    """Nghỉ phép nửa ngày nhưng tick use_compensatory → route sang bù"""
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['MISSING_IN'])
    reason = _reason('Nghỉ phép nửa ngày', full_day=True)
    exp = Explanation.objects.create(
        record=record, employee=base['emp'],
        ci_reason=reason, ci_status='approved',
        ci_use_compensatory=True,
    )
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 4.0
    assert l == 0.0
    assert c == 4.0


@pytest.mark.django_db
def test_calculate_month_creates_compensatory_transaction(base):
    """Khi tính lương, giờ bù được debit vào CompensatoryBalance"""
    s = base
    bal = CompensatoryBalance.objects.create(employee=s['emp'], total_hours=8, used_hours=0)
    record = _record(s['upload'], s['emp'], 1, ['ABSENT'])
    reason = ExplanationReason.objects.create(name='Nghỉ bù cả ngày', is_compensatory=True)
    _explanation(record, s['emp'], ci_reason=reason, ci_status='approved',
                 co_reason=reason, co_status='approved')
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert float(calc.work_hours) == 0.0
    assert float(calc.leave_hours) == 0.0
    bal.refresh_from_db()
    assert float(bal.used_hours) == 8.0
    assert CompensatoryTransaction.objects.filter(
        employee=s['emp'], transaction_type='debit'
    ).exists()


@pytest.mark.django_db
def test_calculate_month_fallback_when_comp_balance_insufficient(base):
    """Nếu giờ bù không đủ, fallback: treat as excused (work = 8, leave = 0)"""
    s = base
    CompensatoryBalance.objects.create(employee=s['emp'], total_hours=2, used_hours=0)
    record = _record(s['upload'], s['emp'], 1, ['ABSENT'])
    reason = ExplanationReason.objects.create(name='Nghỉ bù cả ngày', is_compensatory=True)
    _explanation(record, s['emp'], ci_reason=reason, ci_status='approved',
                 co_reason=reason, co_status='approved')
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    # 8h bù required but only 2h available → fallback: treat as excused, work = 8
    assert float(calc.work_hours) == 8.0
    assert float(calc.leave_hours) == 0.0


@pytest.mark.django_db
def test_calculate_month_fallback_when_leave_balance_insufficient(base):
    """Nếu phép không đủ, fallback: không trừ phép"""
    s = base
    LeaveBalance.objects.create(employee=s['emp'], year=2026, total_days=0)
    record = _record(s['upload'], s['emp'], 1, ['ABSENT'])
    reason = ExplanationReason.objects.create(name='Nghỉ phép cả ngày')
    _explanation(record, s['emp'], ci_reason=reason, ci_status='approved',
                 co_reason=reason, co_status='approved')
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert float(calc.leave_hours) == 0.0

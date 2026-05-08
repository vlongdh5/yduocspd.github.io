import pytest
from datetime import time, date
from unittest.mock import MagicMock
from attendance.error_detector import detect_errors, ErrorCode
from attendance.parser import AttendanceRow


def make_row(check_in=None, check_out=None, shift_code='Ca 8-17'):
    return AttendanceRow(
        employee_code='NV001', employee_name='Test',
        date=date(2026, 5, 1),
        check_in=check_in, check_out=check_out, shift_code=shift_code,
    )


def make_shift(workday_value=1.0, check_in=time(8, 0), check_out=time(17, 0)):
    s = MagicMock()
    s.workday_value = workday_value
    s.check_in = check_in
    s.check_out = check_out
    return s


RULES = {'late_threshold_minutes': 15, 'early_leave_threshold_minutes': 15}


# --- No shift (fallback to rules) ---

def test_no_error_normal_day():
    row = make_row(check_in=time(8, 0), check_out=time(17, 0))
    assert detect_errors(row, rules={}) == []


def test_missing_checkin():
    row = make_row(check_in=None, check_out=time(17, 0))
    assert ErrorCode.MISSING_IN in detect_errors(row, rules={})


def test_missing_checkout():
    row = make_row(check_in=time(8, 0), check_out=None)
    assert ErrorCode.MISSING_OUT in detect_errors(row, rules={})


def test_absent_no_shift():
    row = make_row(check_in=None, check_out=None)
    errors = detect_errors(row, rules={})
    assert errors == [ErrorCode.ABSENT]


def test_late_arrival_rules_fallback():
    row = make_row(check_in=time(8, 16), check_out=time(17, 0))
    rules = {'late_threshold_minutes': 15, 'standard_start': '08:00'}
    assert ErrorCode.LATE in detect_errors(row, rules=rules)


def test_early_leave_rules_fallback():
    row = make_row(check_in=time(8, 0), check_out=time(16, 44))
    rules = {'early_leave_threshold_minutes': 15, 'standard_end': '17:00'}
    assert ErrorCode.EARLY_LEAVE in detect_errors(row, rules=rules)


# --- With shift ---

def test_day_off_shift_no_error():
    """Ca workday=0 (nghỉ tuần, phép...) → không lỗi dù không chấm công."""
    row = make_row(check_in=None, check_out=None, shift_code='Nghỉ tuần theo lịch')
    shift = make_shift(workday_value=0, check_in=time(0, 0), check_out=time(0, 0))
    assert detect_errors(row, rules=RULES, shift=shift) == []


def test_online_shift_no_clock_check():
    """Ca ONLINE (workday=1, in=00:00) → không kiểm tra chấm công."""
    row = make_row(check_in=None, check_out=None, shift_code='ONLINE')
    shift = make_shift(workday_value=1.0, check_in=time(0, 0), check_out=time(0, 0))
    assert detect_errors(row, rules=RULES, shift=shift) == []


def test_holiday_shift_no_clock_check():
    """Nghỉ Lễ tết (workday=1, in=None) → không kiểm tra chấm công."""
    row = make_row(check_in=None, check_out=None, shift_code='Nghỉ Lễ tết')
    shift = make_shift(workday_value=1.0, check_in=None, check_out=None)
    assert detect_errors(row, rules=RULES, shift=shift) == []


def test_late_uses_shift_start_time():
    """LATE so với giờ vào của ca, không phải giờ cố định 08:00."""
    row = make_row(check_in=time(11, 16), check_out=time(20, 0))
    shift = make_shift(workday_value=1.0, check_in=time(11, 0), check_out=time(20, 0))
    assert ErrorCode.LATE in detect_errors(row, rules=RULES, shift=shift)


def test_not_late_with_correct_shift():
    """Vào đúng giờ ca 11-20 → không LATE dù 08:00 rule bảo là muộn."""
    row = make_row(check_in=time(11, 0), check_out=time(20, 0))
    shift = make_shift(workday_value=1.0, check_in=time(11, 0), check_out=time(20, 0))
    assert ErrorCode.LATE not in detect_errors(row, rules=RULES, shift=shift)


def test_early_leave_uses_shift_end_time():
    """EARLY_LEAVE so với giờ ra của ca."""
    row = make_row(check_in=time(8, 0), check_out=time(11, 40))
    shift = make_shift(workday_value=0.5, check_in=time(8, 0), check_out=time(12, 0))
    assert ErrorCode.EARLY_LEAVE in detect_errors(row, rules=RULES, shift=shift)

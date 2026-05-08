import pytest
from datetime import time
from attendance.error_detector import detect_errors, ErrorCode
from attendance.parser import AttendanceRow
from datetime import date


def make_row(check_in=None, check_out=None, shift_code='HC'):
    return AttendanceRow(
        employee_code='NV001', employee_name='Test',
        date=date(2026, 5, 1),
        check_in=check_in, check_out=check_out, shift_code=shift_code
    )


def test_no_error_normal_day():
    row = make_row(check_in=time(8, 0), check_out=time(17, 0))
    errors = detect_errors(row, rules={})
    assert len(errors) == 0


def test_missing_checkin():
    row = make_row(check_in=None, check_out=time(17, 0))
    errors = detect_errors(row, rules={})
    assert ErrorCode.MISSING_IN in errors


def test_missing_checkout():
    row = make_row(check_in=time(8, 0), check_out=None)
    errors = detect_errors(row, rules={})
    assert ErrorCode.MISSING_OUT in errors


def test_absent():
    row = make_row(check_in=None, check_out=None)
    errors = detect_errors(row, rules={})
    assert ErrorCode.ABSENT in errors
    assert ErrorCode.MISSING_IN not in errors


def test_late_arrival():
    row = make_row(check_in=time(8, 16), check_out=time(17, 0))
    rules = {'late_threshold_minutes': 15, 'standard_start': '08:00'}
    errors = detect_errors(row, rules=rules)
    assert ErrorCode.LATE in errors


def test_early_leave():
    row = make_row(check_in=time(8, 0), check_out=time(16, 44))
    rules = {'early_leave_threshold_minutes': 15, 'standard_end': '17:00'}
    errors = detect_errors(row, rules=rules)
    assert ErrorCode.EARLY_LEAVE in errors

from datetime import time, datetime
from enum import Enum
from attendance.parser import AttendanceRow


class ErrorCode(str, Enum):
    MISSING_IN = 'MISSING_IN'
    MISSING_OUT = 'MISSING_OUT'
    ABSENT = 'ABSENT'
    LATE = 'LATE'
    EARLY_LEAVE = 'EARLY_LEAVE'


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _parse_time(s: str) -> time:
    return datetime.strptime(s, '%H:%M').time()


def detect_errors(row: AttendanceRow, rules: dict) -> list:
    if row.check_in is None and row.check_out is None:
        return [ErrorCode.ABSENT]

    errors = []

    if row.check_in is None:
        errors.append(ErrorCode.MISSING_IN)

    if row.check_out is None:
        errors.append(ErrorCode.MISSING_OUT)

    if row.check_in and 'standard_start' in rules:
        standard = _parse_time(rules['standard_start'])
        threshold = rules.get('late_threshold_minutes', 15)
        if _to_minutes(row.check_in) > _to_minutes(standard) + threshold:
            errors.append(ErrorCode.LATE)

    if row.check_out and 'standard_end' in rules:
        standard = _parse_time(rules['standard_end'])
        threshold = rules.get('early_leave_threshold_minutes', 15)
        if _to_minutes(row.check_out) < _to_minutes(standard) - threshold:
            errors.append(ErrorCode.EARLY_LEAVE)

    return errors

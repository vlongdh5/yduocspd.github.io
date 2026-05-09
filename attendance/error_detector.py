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


def _shift_has_clock_times(shift) -> bool:
    """Shift có giờ vào/ra thực tế (không phải null hoặc 00:00 sentinel)."""
    sentinel = time(0, 0)
    return (
        shift.check_in is not None and shift.check_in != sentinel and
        shift.check_out is not None and shift.check_out != sentinel
    )


def detect_errors(row: AttendanceRow, rules: dict, shift=None) -> list:
    # Ca không cần đi làm (nghỉ tuần, phép, OFF...) → không lỗi
    if shift is not None and float(shift.workday_value) == 0:
        return []

    # Ca có workday > 0 nhưng không định nghĩa giờ cụ thể (ONLINE, Nghỉ Lễ tết)
    # → không kiểm tra chấm công
    if shift is not None and not _shift_has_clock_times(shift):
        return []

    # Từ đây: ca có giờ thật, hoặc không tìm thấy ca (fallback)
    if row.check_in is None and row.check_out is None:
        return [ErrorCode.ABSENT]

    errors = []

    if row.check_in is None:
        errors.append(ErrorCode.MISSING_IN)

    if row.check_out is None:
        errors.append(ErrorCode.MISSING_OUT)

    # LATE — bất kỳ check_in nào sau shift_start (không có ngưỡng)
    if row.check_in:
        if shift is not None and _shift_has_clock_times(shift):
            standard_in = shift.check_in
        elif 'standard_start' in rules:
            standard_in = _parse_time(rules['standard_start'])
        else:
            standard_in = None

        if standard_in and _to_minutes(row.check_in) > _to_minutes(standard_in):
            errors.append(ErrorCode.LATE)

    # EARLY_LEAVE — bất kỳ check_out nào trước shift_end (không có ngưỡng)
    if row.check_out:
        if shift is not None and _shift_has_clock_times(shift):
            standard_out = shift.check_out
        elif 'standard_end' in rules:
            standard_out = _parse_time(rules['standard_end'])
        else:
            standard_out = None

        if standard_out and _to_minutes(row.check_out) < _to_minutes(standard_out):
            errors.append(ErrorCode.EARLY_LEAVE)

    return errors

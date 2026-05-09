from datetime import time
from attendance.models import AttendanceUpload, AttendanceRecord, ErrorType, Shift
from attendance.parser import AttendanceRow
from attendance.error_detector import detect_errors, ErrorCode, _to_minutes, _parse_time, _shift_has_clock_times
from employees.models import Employee


def _build_rules() -> dict:
    rules = {}
    for et in ErrorType.objects.filter(is_active=True):
        if et.detection_rule:
            rules.update(et.detection_rule)
    return rules


def _compute_minutes_late(row: AttendanceRow, rules: dict, shift) -> int | None:
    if row.check_in is None:
        return None
    if shift is not None and _shift_has_clock_times(shift):
        standard_in = shift.check_in
    elif 'standard_start' in rules:
        standard_in = _parse_time(rules['standard_start'])
    else:
        return None
    diff = _to_minutes(row.check_in) - _to_minutes(standard_in)
    return diff if diff > 0 else None


def _compute_minutes_early(row: AttendanceRow, rules: dict, shift) -> int | None:
    if row.check_out is None:
        return None
    if shift is not None and _shift_has_clock_times(shift):
        standard_out = shift.check_out
    elif 'standard_end' in rules:
        standard_out = _parse_time(rules['standard_end'])
    else:
        return None
    diff = _to_minutes(standard_out) - _to_minutes(row.check_out)
    return diff if diff > 0 else None


def process_upload(upload: AttendanceUpload, rows: list):
    employee_map = {emp.code: emp for emp in Employee.objects.filter(is_active=True)}
    shift_map = {s.code: s for s in Shift.objects.filter(is_active=True)}
    rules = _build_rules()
    total = 0
    errors = 0

    for row in rows:
        emp = employee_map.get(row.employee_code)
        if not emp:
            continue

        shift = shift_map.get(row.shift_code)
        error_codes = detect_errors(row, rules, shift=shift)
        status = 'error' if error_codes else 'ok'

        minutes_late = _compute_minutes_late(row, rules, shift) if ErrorCode.LATE in error_codes else None
        minutes_early = _compute_minutes_early(row, rules, shift) if ErrorCode.EARLY_LEAVE in error_codes else None

        AttendanceRecord.objects.update_or_create(
            upload=upload,
            employee=emp,
            date=row.date,
            defaults={
                'check_in': row.check_in,
                'check_out': row.check_out,
                'shift_code': row.shift_code,
                'status': status,
                'error_types': [e.value for e in error_codes],
                'minutes_late': minutes_late,
                'minutes_early': minutes_early,
            }
        )
        total += 1
        if status == 'error':
            errors += 1

    upload.total_records = total
    upload.error_records = errors
    upload.status = AttendanceUpload.Status.DONE
    upload.save()

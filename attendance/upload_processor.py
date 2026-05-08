from attendance.models import AttendanceUpload, AttendanceRecord, ErrorType
from attendance.parser import AttendanceRow
from attendance.error_detector import detect_errors
from employees.models import Employee


def _build_rules() -> dict:
    rules = {}
    for et in ErrorType.objects.filter(is_active=True):
        if et.detection_rule:
            rules.update(et.detection_rule)
    return rules


def process_upload(upload: AttendanceUpload, rows: list):
    employee_map = {emp.code: emp for emp in Employee.objects.filter(is_active=True)}
    rules = _build_rules()
    total = 0
    errors = 0

    for row in rows:
        emp = employee_map.get(row.employee_code)
        if not emp:
            continue

        error_codes = detect_errors(row, rules)
        status = 'error' if error_codes else 'ok'

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
            }
        )
        total += 1
        if status == 'error':
            errors += 1

    upload.total_records = total
    upload.error_records = errors
    upload.status = AttendanceUpload.Status.DONE
    upload.save()

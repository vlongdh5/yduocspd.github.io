from decimal import Decimal
from attendance.models import AttendanceRecord
from explanations.models import Explanation
from employees.models import Employee
from reports.models import AttendanceCalculation
from accounts.models import User


def calculate_month(month: str, calculated_by: User) -> dict:
    records = AttendanceRecord.objects.filter(
        upload__month=month
    ).select_related('employee', 'explanation')

    results = {}

    for record in records:
        code = record.employee.code
        if code not in results:
            results[code] = {'employee': record.employee, 'workdays': Decimal(0), 'leave': Decimal(0)}

        if record.status == 'ok':
            results[code]['workdays'] += Decimal(1)
        elif record.status == 'error':
            exp = getattr(record, 'explanation', None)
            if exp and exp.status == Explanation.Status.APPROVED:
                results[code]['workdays'] += Decimal(1)
            else:
                results[code]['leave'] += Decimal(1)

    calcs = {}
    for code, data in results.items():
        emp = data['employee']
        calc, _ = AttendanceCalculation.objects.update_or_create(
            employee=emp,
            month=month,
            defaults={
                'actual_workdays': data['workdays'],
                'leave_days_used': data['leave'],
                'calculated_by': calculated_by,
                'status': AttendanceCalculation.Status.DRAFT,
            }
        )
        calcs[code] = calc

    return calcs

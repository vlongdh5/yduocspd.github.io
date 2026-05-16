import calendar
from decimal import Decimal
from datetime import date as _date, time
from attendance.models import AttendanceRecord, Shift
from explanations.models import Explanation
from employees.models import Employee, LeaveBalance, CompensatoryBalance, CompensatoryTransaction
from reports.models import AttendanceCalculation
from accounts.models import User


LEAVE_REASONS = {'Đi muộn/ Về sớm'}     # approved → minutes counted as leave, work reduced
EXCUSED_REASONS = {
    'Quên chấm công',
    'Trị liệu tại nhà',
    'Đi công tác/ tổ chức sự kiện/ công việc khác theo chỉ đạo',
}
LEAVE_FULL_DAY_REASONS = {'Nghỉ phép cả ngày'}
LEAVE_HALF_DAY_REASONS = {'Nghỉ phép nửa ngày'}
UNPAID_REASONS = {'Nghỉ không lương'}
QCC_REASON = 'Quên chấm công'


class RC:
    """
    Internal result codes for per-session attendance calculation.

    Code            | Tiếng Việt          | Ý nghĩa
    ----------------|---------------------|----------------------------------------
    OK              | Công                | Không lỗi / đã tha — không trừ gì
    DAY_OFF         | Nghỉ phép           | Nghỉ phép cả ngày — trừ vào phép
    UNEXCUSED       | Không (trừ phút)    | LATE/EARLY chưa duyệt — trừ đúng phút
    UNEXCUSED_BLOCK | Không (trừ block)   | MISSING_IN/OUT chưa duyệt — trừ cả nửa ngày
    LEAVE           | Phép (phút)         | Duyệt phép — phút trừ vào số giờ phép
    LEAVE_BLOCK     | Phép (nửa ngày)     | Duyệt nghỉ nửa ngày — block trừ vào số giờ phép
    UNPAID_BLOCK    | NKL (nửa ngày)      | Nghỉ không lương nửa buổi — trừ block khỏi công, không trừ phép
    """
    OK = 'OK'
    DAY_OFF = 'DAY_OFF'
    UNEXCUSED = 'UNEXCUSED'
    UNEXCUSED_BLOCK = 'UNEXCUSED_BLOCK'
    LEAVE = 'LEAVE'
    LEAVE_BLOCK = 'LEAVE_BLOCK'
    UNPAID_BLOCK = 'UNPAID_BLOCK'


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _break_minutes(shift: Shift) -> int:
    if shift and shift.break_start and shift.break_end:
        return _to_minutes(shift.break_end) - _to_minutes(shift.break_start)
    return 0


def _morning_block_hours(shift: Shift) -> float:
    if shift and shift.check_in and shift.break_start:
        return (_to_minutes(shift.break_start) - _to_minutes(shift.check_in)) / 60
    if shift and shift.check_in and shift.check_out:
        total = (_to_minutes(shift.check_out) - _to_minutes(shift.check_in)) / 60
        return round(total / 2, 2)
    return 4.0


def _afternoon_block_hours(shift: Shift) -> float:
    if shift and shift.break_end and shift.check_out:
        return (_to_minutes(shift.check_out) - _to_minutes(shift.break_end)) / 60
    if shift and shift.check_in and shift.check_out:
        total = (_to_minutes(shift.check_out) - _to_minutes(shift.check_in)) / 60
        return round(total / 2, 2)
    return 4.0


def _ci_result(error_set, ci_reason, ci_approved):
    """Determine result code for CI (check-in) side."""
    has_ci = bool(error_set & {'LATE', 'MISSING_IN'})
    if not has_ci:
        return RC.OK
    if not ci_approved or ci_reason is None:
        return RC.UNEXCUSED_BLOCK if 'MISSING_IN' in error_set else RC.UNEXCUSED
    rn = ci_reason.name
    if rn in LEAVE_HALF_DAY_REASONS:
        return RC.LEAVE_BLOCK
    if ci_reason.is_compensatory:
        if ci_reason.requires_full_day_shift:
            return RC.LEAVE_BLOCK
        return RC.DAY_OFF
    if rn in LEAVE_FULL_DAY_REASONS:
        return RC.DAY_OFF
    if rn in UNPAID_REASONS:
        return RC.UNPAID_BLOCK
    if rn in LEAVE_REASONS:
        return RC.LEAVE
    return RC.OK  # EXCUSED_REASONS and any unknown approved = excused


def _co_result(error_set, co_reason, co_approved):
    """Determine result code for CO (check-out) side."""
    has_co = bool(error_set & {'EARLY_LEAVE', 'MISSING_OUT'})
    if not has_co:
        return RC.OK
    if not co_approved or co_reason is None:
        return RC.UNEXCUSED_BLOCK if 'MISSING_OUT' in error_set else RC.UNEXCUSED
    rn = co_reason.name
    if rn in LEAVE_HALF_DAY_REASONS:
        return RC.LEAVE_BLOCK
    if co_reason.is_compensatory:
        if co_reason.requires_full_day_shift:
            return RC.LEAVE_BLOCK
        return RC.DAY_OFF
    if rn in LEAVE_FULL_DAY_REASONS:
        return RC.DAY_OFF
    if rn in UNPAID_REASONS:
        return RC.UNPAID_BLOCK
    if rn in LEAVE_REASONS:
        return RC.LEAVE
    return RC.OK


def _effective_minutes(minutes, block_min, break_min):
    """Remove break time from late/early count when the span crosses into the break period."""
    if minutes <= block_min:
        return minutes
    return minutes - min(break_min, minutes - block_min)


def _apply_adj(result, minutes, shift, session):
    """Returns (Δwork_hours, Δleave_hours). Negative = deduction."""
    if result in (RC.OK, RC.DAY_OFF):
        return 0.0, 0.0
    m = minutes or 0
    if result in (RC.UNEXCUSED, RC.LEAVE):
        # Subtract break time if late/early span crosses the half-day boundary
        if shift and m > 0:
            block_min = (_morning_block_hours(shift) if session == 'morning'
                         else _afternoon_block_hours(shift)) * 60
            m = _effective_minutes(m, block_min, _break_minutes(shift))
        h = m / 60
        return (-h, h) if result == RC.LEAVE else (-h, 0.0)
    if result == RC.UNEXCUSED_BLOCK:
        block = _morning_block_hours(shift) if session == 'morning' else _afternoon_block_hours(shift)
        return -block, 0.0
    if result == RC.UNPAID_BLOCK:
        block = _morning_block_hours(shift) if session == 'morning' else _afternoon_block_hours(shift)
        return -block, 0.0
    if result == RC.LEAVE_BLOCK:
        block = _morning_block_hours(shift) if session == 'morning' else _afternoon_block_hours(shift)
        return -block, block
    return 0.0, 0.0


def _is_qcc_record(exp):
    """True if this record has an approved QCC explanation on either side."""
    if exp is None:
        return False
    ci_qcc = (exp.ci_reason and exp.ci_reason.name == QCC_REASON
              and exp.ci_status == Explanation.Status.APPROVED)
    co_qcc = (exp.co_reason and exp.co_reason.name == QCC_REASON
              and exp.co_status == Explanation.Status.APPROVED)
    return ci_qcc or co_qcc


def compute_record_hours(record, exp, shift, qcc_count):
    """
    Compute (work_hours, leave_hours, compensatory_hours) for a single attendance record.

    qcc_count: cumulative QCC occurrences up to and including this record for the employee this month.
    """
    error_set = set(record.error_types)
    base_work = float(shift.work_hours) if shift else 8.0
    base_leave = float(shift.leave_hours) if shift else 0.0

    if not error_set:
        return base_work, base_leave, 0.0

    ci_reason = exp.ci_reason if exp else None
    co_reason = exp.co_reason if exp else None
    ci_approved = bool(exp and exp.ci_status == Explanation.Status.APPROVED)
    co_approved = bool(exp and exp.co_status == Explanation.Status.APPROVED)
    ci_use_comp = bool(exp and exp.ci_use_compensatory)
    co_use_comp = bool(exp and exp.co_use_compensatory)

    if 'ABSENT' in error_set:
        reason = ci_reason or co_reason
        approved = ci_approved or co_approved
        use_comp = ci_use_comp or co_use_comp
        if approved and reason:
            if reason.is_compensatory or use_comp:
                return 0.0, 0.0, base_work
            if reason.name in LEAVE_FULL_DAY_REASONS:
                return 0.0, base_work, 0.0
            if reason.name in UNPAID_REASONS:
                return 0.0, 0.0, 0.0
            if reason.name in EXCUSED_REASONS:
                if _is_qcc_record(exp) and qcc_count >= 3:
                    half = round(base_work / 2, 2)
                    return half, half, 0.0
                return base_work, base_leave, 0.0
        return 0.0, 0.0, 0.0

    result_ci = _ci_result(error_set, ci_reason, ci_approved)
    result_co = _co_result(error_set, co_reason, co_approved)

    if result_ci == RC.UNPAID_BLOCK and result_co == RC.UNPAID_BLOCK:
        return 0.0, 0.0, 0.0

    if result_ci == RC.DAY_OFF and result_co == RC.DAY_OFF:
        ci_comp = ci_reason and ci_reason.is_compensatory
        co_comp = co_reason and co_reason.is_compensatory
        if ci_comp or co_comp:
            return 0.0, 0.0, base_work
        ci_leave = ci_reason and ci_reason.name in LEAVE_FULL_DAY_REASONS
        co_leave = co_reason and co_reason.name in LEAVE_FULL_DAY_REASONS
        if ci_leave or co_leave:
            return 0.0, base_work, 0.0
        return 0.0, 0.0, 0.0

    d_work_ci, d_leave_ci = _apply_adj(result_ci, record.minutes_late, shift, 'morning')
    d_work_co, d_leave_co = _apply_adj(result_co, record.minutes_early, shift, 'afternoon')

    comp = 0.0
    if (ci_use_comp or (ci_reason and ci_reason.is_compensatory)) and d_leave_ci > 0:
        comp += d_leave_ci
        d_leave_ci = 0.0
    if (co_use_comp or (co_reason and co_reason.is_compensatory)) and d_leave_co > 0:
        comp += d_leave_co
        d_leave_co = 0.0

    work = base_work + d_work_ci + d_work_co
    leave = base_leave + d_leave_ci + d_leave_co

    if result_ci == RC.LEAVE_BLOCK and record.minutes_late and shift:
        overflow = record.minutes_late - _morning_block_hours(shift) * 60 - _break_minutes(shift)
        if overflow > 0:
            work -= overflow / 60
            if ci_use_comp or (ci_reason and ci_reason.is_compensatory):
                comp += overflow / 60
            else:
                leave += overflow / 60

    if result_co == RC.LEAVE_BLOCK and record.minutes_early and shift:
        overflow = record.minutes_early - _afternoon_block_hours(shift) * 60 - _break_minutes(shift)
        if overflow > 0:
            work -= overflow / 60
            if co_use_comp or (co_reason and co_reason.is_compensatory):
                comp += overflow / 60
            else:
                leave += overflow / 60

    work = max(work, 0.0)

    if _is_qcc_record(exp) and qcc_count >= 3:
        half = round(work / 2, 2)
        leave += half
        work = half

    return round(work, 2), round(leave, 2), round(comp, 2)


def _validate_month(month: str) -> dict:
    """
    Return {'not_submitted': [...codes], 'not_approved': [...codes]}.
    not_submitted: employee hasn't filled in a reason yet.
    not_approved:  reason submitted but still pending or rejected (not approved by TBP).
    """
    not_submitted = set()
    not_approved = set()

    records = AttendanceRecord.objects.filter(
        upload__month=month, status='error'
    ).select_related('explanation')

    for record in records:
        exp = getattr(record, 'explanation', None)
        needs_ci = record.has_ci_issue
        needs_co = record.has_co_issue

        ci_submitted = exp and exp.ci_reason_id is not None
        co_submitted = exp and exp.co_reason_id is not None
        ci_pending = exp and exp.ci_status == Explanation.Status.PENDING
        co_pending = exp and exp.co_status == Explanation.Status.PENDING

        if (needs_ci and not ci_submitted) or (needs_co and not co_submitted):
            not_submitted.add(record.employee.code)
        elif (needs_ci and ci_pending) or (needs_co and co_pending):
            not_approved.add(record.employee.code)
        # rejected = TBP đã xử lý xong (từ chối), tính công bình thường (NV bị trừ)

    return {'not_submitted': sorted(not_submitted), 'not_approved': sorted(not_approved)}


def calculate_month(month: str, calculated_by: User) -> dict:
    issues = _validate_month(month)
    errors = []
    if issues['not_submitted']:
        errors.append(f'{len(issues["not_submitted"])} NV chưa nộp giải trình: {", ".join(issues["not_submitted"])}')
    if issues['not_approved']:
        errors.append(f'{len(issues["not_approved"])} NV còn giải trình chờ TBP duyệt: {", ".join(issues["not_approved"])}')
    if errors:
        raise ValueError(' | '.join(errors))

    records = AttendanceRecord.objects.filter(
        upload__month=month
    ).select_related(
        'employee', 'explanation__ci_reason', 'explanation__co_reason'
    ).order_by('employee__code', 'date')

    shift_map = {s.code: s for s in Shift.objects.filter(is_active=True)}

    # Group records by employee
    by_employee: dict[str, list] = {}
    for record in records:
        code = record.employee.code
        if code not in by_employee:
            by_employee[code] = []
        by_employee[code].append(record)

    calcs = {}
    for code, emp_records in by_employee.items():
        emp = emp_records[0].employee
        total_work = 0.0
        total_leave = 0.0
        total_compensatory = 0.0
        qcc_count = 0

        lb = LeaveBalance.objects.filter(
            employee=emp, year=int(month[:4])
        ).first()
        # None means no balance record → no constraint; non-None means apply running constraint
        running_leave_remaining = float(lb.remaining_days * 8) if lb is not None else None
        comp_balance, _ = CompensatoryBalance.objects.get_or_create(employee=emp)
        # Undo previous debit for this month so recalculation is idempotent
        existing_debit = CompensatoryTransaction.objects.filter(
            employee=emp,
            transaction_type=CompensatoryTransaction.Type.DEBIT,
            note=f'Tính công tháng {month}',
        ).first()
        if existing_debit:
            comp_balance.used_hours -= existing_debit.hours
            comp_balance.save()
            existing_debit.delete()
        running_comp_remaining = float(comp_balance.remaining_hours)

        for record in emp_records:
            exp = getattr(record, 'explanation', None)
            shift = shift_map.get(record.shift_code) if record.shift_code else None

            if _is_qcc_record(exp):
                qcc_count += 1

            w, l, c = compute_record_hours(record, exp, shift, qcc_count)

            if c > 0 and running_comp_remaining - c < 0:
                # Insufficient comp balance: treat as excused (work full shift, no leave, no comp)
                w = float(shift.work_hours) if shift else 8.0
                l = 0.0
                c = 0.0

            if l > 0 and running_leave_remaining is not None and running_leave_remaining - l < 0:
                if w == 0.0:
                    # ABSENT record: restore work hours so employee isn't penalized as unpaid
                    w = float(shift.work_hours) if shift else 8.0
                l = 0.0

            running_comp_remaining -= c
            if running_leave_remaining is not None:
                running_leave_remaining -= l
            total_work += w
            total_leave += l
            total_compensatory += c

        total_work = round(total_work, 2)
        total_leave = round(total_leave, 2)
        total_compensatory = round(total_compensatory, 2)

        calc, _ = AttendanceCalculation.objects.update_or_create(
            employee=emp,
            month=month,
            defaults={
                'work_hours': Decimal(str(total_work)),
                'leave_hours': Decimal(str(total_leave)),
                'actual_workdays': Decimal(str(round(total_work / 8, 2))),
                'leave_days_used': Decimal(str(round(total_leave / 8, 2))),
                'calculated_by': calculated_by,
                'status': AttendanceCalculation.Status.DRAFT,
            }
        )

        if total_compensatory > 0:
            comp_balance.used_hours = Decimal(str(
                float(comp_balance.used_hours) + total_compensatory
            ))
            comp_balance.save()
            last_day = calendar.monthrange(int(month[:4]), int(month[5:]))[1]
            CompensatoryTransaction.objects.create(
                employee=emp,
                balance=comp_balance,
                transaction_type=CompensatoryTransaction.Type.DEBIT,
                hours=Decimal(str(total_compensatory)),
                date=_date(int(month[:4]), int(month[5:]), last_day),
                note=f'Tính công tháng {month}',
                created_by=calculated_by,
            )

        calcs[code] = calc

    return calcs

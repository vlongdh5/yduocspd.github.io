from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Explanation, ExplanationReason
from attendance.models import AttendanceRecord, Shift
from reports.models import AttendanceCalculation


def _is_month_finalized(employee, month):
    return AttendanceCalculation.objects.filter(
        employee=employee, month=month, status=AttendanceCalculation.Status.FINALIZED
    ).exists()


def _dept_filter(qs, user):
    if user.is_tbp and not user.is_hr:
        dept = user.managed_departments.first()
        if dept:
            return qs.filter(employee__department=dept)
        return qs.none()
    return qs


def _get_shift(record):
    if record.shift_code:
        return Shift.objects.filter(code=record.shift_code, is_active=True).first()
    return None


def _reasons_for_shift(shift):
    qs = ExplanationReason.objects.filter(is_active=True)
    if shift is None or float(shift.workday_value) != 1:
        qs = qs.filter(requires_full_day_shift=False)
    return qs


@login_required
def submit_explanation(request, record_id):
    record = get_object_or_404(AttendanceRecord, pk=record_id, employee=request.user.employee_profile)
    exp = getattr(record, 'explanation', None)

    shift = _get_shift(record)
    reasons = _reasons_for_shift(shift)

    has_ci = record.has_ci_issue
    has_co = record.has_co_issue

    # Block if both sides approved
    ci_locked = exp and exp.ci_status == Explanation.Status.APPROVED
    co_locked = exp and exp.co_status == Explanation.Status.APPROVED
    if ci_locked and co_locked:
        messages.info(request, 'Giải trình này đã được duyệt hoàn toàn.')
        return redirect('attendance:my_attendance')

    if request.method == 'POST':
        ci_reason_id = request.POST.get('ci_reason')
        ci_note = request.POST.get('ci_note', '').strip()
        co_reason_id = request.POST.get('co_reason')
        co_note = request.POST.get('co_note', '').strip()

        ci_changed = has_ci and not ci_locked and ci_reason_id
        co_changed = has_co and not co_locked and co_reason_id

        if not ci_changed and not co_changed:
            messages.warning(request, 'Vui lòng chọn lý do giải trình.')
            return redirect('attendance:my_attendance')

        if exp is None:
            exp = Explanation(record=record, employee=request.user.employee_profile)

        if ci_changed:
            exp.ci_reason = get_object_or_404(ExplanationReason, pk=ci_reason_id, is_active=True)
            exp.ci_note = ci_note
            exp.ci_status = Explanation.Status.PENDING
            exp.ci_reviewed_by = None
            exp.ci_reviewed_at = None
            exp.ci_reviewer_note = ''

        if co_changed:
            exp.co_reason = get_object_or_404(ExplanationReason, pk=co_reason_id, is_active=True)
            exp.co_note = co_note
            exp.co_status = Explanation.Status.PENDING
            exp.co_reviewed_by = None
            exp.co_reviewed_at = None
            exp.co_reviewer_note = ''

        exp.save()
        messages.success(request, 'Giải trình đã được nộp.')
        return redirect('attendance:my_attendance')

    return render(request, 'explanations/submit.html', {
        'record': record,
        'exp': exp,
        'reasons': reasons,
        'has_ci': has_ci,
        'has_co': has_co,
        'ci_locked': ci_locked,
        'co_locked': co_locked,
    })


@login_required
def my_explanations(request):
    explanations = Explanation.objects.filter(
        employee=request.user.employee_profile
    ).select_related('ci_reason', 'co_reason', 'record').order_by('-submitted_at')
    return render(request, 'explanations/my_explanations.html', {'explanations': explanations})


@login_required
def pending_approvals(request):
    if not (request.user.is_tbp or request.user.is_hr):
        return redirect('attendance:my_attendance')

    base_qs = Explanation.objects.select_related(
        'employee__department', 'record__upload', 'ci_reason', 'co_reason',
        'ci_reviewed_by', 'co_reviewed_by'
    )

    from django.db.models import Q

    # Chờ duyệt: ít nhất 1 phía có ci/co_status = pending
    pending = _dept_filter(
        base_qs.filter(
            Q(ci_status=Explanation.Status.PENDING) | Q(co_status=Explanation.Status.PENDING)
        ),
        request.user
    ).order_by('record__date')

    # Đã xử lý: không còn phía nào pending, nhưng có ít nhất 1 phía đã duyệt/từ chối
    reviewed = _dept_filter(
        base_qs.exclude(
            Q(ci_status=Explanation.Status.PENDING) | Q(co_status=Explanation.Status.PENDING)
        ).filter(
            Q(ci_status__in=[Explanation.Status.APPROVED, Explanation.Status.REJECTED]) |
            Q(co_status__in=[Explanation.Status.APPROVED, Explanation.Status.REJECTED])
        ),
        request.user
    ).order_by('-submitted_at')

    reviewed_with_lock = []
    for exp in reviewed:
        month = exp.record.upload.month if exp.record.upload_id else None
        locked = _is_month_finalized(exp.employee, month) if month else False
        reviewed_with_lock.append((exp, locked))

    return render(request, 'explanations/pending_approvals.html', {
        'pending': pending,
        'reviewed_with_lock': reviewed_with_lock,
    })


@login_required
def review_explanation(request, pk):
    if not (request.user.is_tbp or request.user.is_hr):
        return redirect('attendance:my_attendance')

    qs = Explanation.objects.select_related(
        'record__upload', 'employee', 'ci_reason', 'co_reason',
        'ci_reviewed_by', 'co_reviewed_by'
    )
    exp = get_object_or_404(_dept_filter(qs, request.user), pk=pk)

    month = exp.record.upload.month if exp.record.upload_id else None
    locked = _is_month_finalized(exp.employee, month) if month else False

    if request.method == 'POST':
        if locked:
            messages.error(request, 'Tháng này đã được chốt công, không thể thay đổi phê duyệt.')
            return redirect('explanations:pending_approvals')

        action = request.POST.get('action')
        side = request.POST.get('side')
        reviewer_note = request.POST.get('reviewer_note', '').strip()

        if side == 'ci' and exp.has_ci_issue:
            if action == 'reset' and exp.ci_status in (Explanation.Status.APPROVED, Explanation.Status.REJECTED):
                exp.ci_status = Explanation.Status.PENDING
                exp.ci_reviewed_by = None
                exp.ci_reviewed_at = None
                exp.ci_reviewer_note = ''
                exp.save()
                messages.success(request, 'Đã đặt lại CI về Chờ duyệt.')
            elif action in ('approve', 'reject') and exp.ci_status in (
                Explanation.Status.PENDING,
                Explanation.Status.APPROVED,
                Explanation.Status.REJECTED,
            ):
                new_status = Explanation.Status.APPROVED if action == 'approve' else Explanation.Status.REJECTED
                exp.ci_status = new_status
                exp.ci_reviewed_by = request.user
                exp.ci_reviewed_at = timezone.now()
                exp.ci_reviewer_note = reviewer_note
                exp.save()
                messages.success(request, f'Đã {"duyệt" if action == "approve" else "từ chối"} giải trình Check-in.')
        elif side == 'co' and exp.has_co_issue:
            if action == 'reset' and exp.co_status in (Explanation.Status.APPROVED, Explanation.Status.REJECTED):
                exp.co_status = Explanation.Status.PENDING
                exp.co_reviewed_by = None
                exp.co_reviewed_at = None
                exp.co_reviewer_note = ''
                exp.save()
                messages.success(request, 'Đã đặt lại CO về Chờ duyệt.')
            elif action in ('approve', 'reject') and exp.co_status in (
                Explanation.Status.PENDING,
                Explanation.Status.APPROVED,
                Explanation.Status.REJECTED,
            ):
                new_status = Explanation.Status.APPROVED if action == 'approve' else Explanation.Status.REJECTED
                exp.co_status = new_status
                exp.co_reviewed_by = request.user
                exp.co_reviewed_at = timezone.now()
                exp.co_reviewer_note = reviewer_note
                exp.save()
                messages.success(request, f'Đã {"duyệt" if action == "approve" else "từ chối"} giải trình Check-out.')

        # Nếu cả 2 phía đều đã xử lý xong → về danh sách, còn pending → ở lại
        exp.refresh_from_db()
        still_pending = (
            (exp.has_ci_issue and exp.ci_status == Explanation.Status.PENDING) or
            (exp.has_co_issue and exp.co_status == Explanation.Status.PENDING)
        )
        if still_pending:
            return redirect('explanations:review', pk=exp.pk)
        return redirect('explanations:pending_approvals')

    return render(request, 'explanations/review.html', {'exp': exp, 'locked': locked})


@login_required
def bulk_review(request):
    if not (request.user.is_tbp or request.user.is_hr):
        return redirect('attendance:my_attendance')
    if request.method != 'POST':
        return redirect('explanations:pending_approvals')

    action = request.POST.get('action')
    if action not in ('approve', 'reject'):
        return redirect('explanations:pending_approvals')

    raw_ids = request.POST.getlist('exp_ids')
    if not raw_ids:
        messages.warning(request, 'Chưa chọn giải trình nào.')
        return redirect('explanations:pending_approvals')
    try:
        ids = [int(i) for i in raw_ids]
    except (ValueError, TypeError):
        messages.error(request, 'Dữ liệu không hợp lệ.')
        return redirect('explanations:pending_approvals')

    qs = Explanation.objects.filter(pk__in=ids)
    # TBP chỉ được duyệt phòng ban mình quản lý
    if request.user.is_tbp and not request.user.is_hr:
        dept = request.user.managed_departments.first()
        if dept:
            qs = qs.filter(employee__department=dept)

    now = timezone.now()
    count = 0
    status = Explanation.Status.APPROVED if action == 'approve' else Explanation.Status.REJECTED

    for exp in qs.select_related('record'):
        month = exp.record.upload.month if exp.record.upload_id else None
        if month and _is_month_finalized(exp.employee, month):
            continue
        changed = False
        if exp.has_ci_issue and exp.ci_status == Explanation.Status.PENDING:
            exp.ci_status = status
            exp.ci_reviewed_by = request.user
            exp.ci_reviewed_at = now
            changed = True
        if exp.has_co_issue and exp.co_status == Explanation.Status.PENDING:
            exp.co_status = status
            exp.co_reviewed_by = request.user
            exp.co_reviewed_at = now
            changed = True
        if changed:
            exp.save()
            count += 1

    label = 'phê duyệt' if action == 'approve' else 'từ chối'
    messages.success(request, f'Đã {label} {count} giải trình.')
    return redirect('explanations:pending_approvals')

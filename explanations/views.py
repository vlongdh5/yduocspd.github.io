from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Explanation, ExplanationReason
from attendance.models import AttendanceRecord
from reports.models import AttendanceCalculation


def _is_month_finalized(employee, month):
    return AttendanceCalculation.objects.filter(
        employee=employee, month=month, status=AttendanceCalculation.Status.FINALIZED
    ).exists()


def _dept_filter(qs, user):
    """Lọc theo phòng ban nếu là TBP (không phải HR)."""
    if user.is_tbp and not user.is_hr:
        dept = user.managed_departments.first()
        if dept:
            return qs.filter(employee__department=dept)
        return qs.none()
    return qs


@login_required
def submit_explanation(request, record_id):
    record = get_object_or_404(AttendanceRecord, pk=record_id, employee=request.user.employee_profile)
    existing = getattr(record, 'explanation', None)

    if existing and existing.status == Explanation.Status.APPROVED:
        messages.info(request, 'Giải trình này đã được duyệt.')
        return redirect('attendance:my_attendance')

    reasons = ExplanationReason.objects.filter(is_active=True)

    if request.method == 'POST':
        reason_id = request.POST.get('reason')
        note = request.POST.get('note', '').strip()
        reason = get_object_or_404(ExplanationReason, pk=reason_id, is_active=True)

        if existing:
            existing.reason = reason
            existing.note = note
            existing.status = Explanation.Status.PENDING
            existing.reviewed_by = None
            existing.reviewed_at = None
            existing.reviewer_note = ''
            existing.save()
        else:
            Explanation.objects.create(
                record=record, employee=request.user.employee_profile,
                reason=reason, note=note
            )
        messages.success(request, 'Giải trình đã được nộp.')
        return redirect('attendance:my_attendance')

    return render(request, 'explanations/submit.html', {
        'record': record, 'reasons': reasons, 'existing': existing
    })


@login_required
def my_explanations(request):
    explanations = Explanation.objects.filter(
        employee=request.user.employee_profile
    ).select_related('reason', 'record', 'reviewed_by').order_by('-submitted_at')
    return render(request, 'explanations/my_explanations.html', {'explanations': explanations})


@login_required
def pending_approvals(request):
    if not (request.user.is_tbp or request.user.is_hr):
        return redirect('attendance:my_attendance')

    base_qs = Explanation.objects.select_related(
        'employee__department', 'record__upload', 'reason', 'reviewed_by'
    )

    pending = _dept_filter(
        base_qs.filter(status=Explanation.Status.PENDING),
        request.user
    ).order_by('record__date')

    reviewed = _dept_filter(
        base_qs.filter(status__in=[Explanation.Status.APPROVED, Explanation.Status.REJECTED]),
        request.user
    ).order_by('-reviewed_at')

    # Đánh dấu từng giải trình đã xử lý có bị khoá (tháng đã chốt) hay không
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

    exp = get_object_or_404(
        Explanation.objects.select_related('record__upload', 'employee', 'reason'),
        pk=pk
    )

    month = exp.record.upload.month if exp.record.upload_id else None
    locked = _is_month_finalized(exp.employee, month) if month else False

    if request.method == 'POST':
        if locked:
            messages.error(request, 'Tháng này đã được chốt công, không thể thay đổi phê duyệt.')
            return redirect('explanations:pending_approvals')

        action = request.POST.get('action')
        reviewer_note = request.POST.get('reviewer_note', '').strip()
        if action == 'approve':
            exp.status = Explanation.Status.APPROVED
        elif action == 'reject':
            exp.status = Explanation.Status.REJECTED
        exp.reviewed_by = request.user
        exp.reviewed_at = timezone.now()
        exp.reviewer_note = reviewer_note
        exp.save()
        messages.success(request, f'Đã {"duyệt" if action == "approve" else "từ chối"} giải trình.')
        return redirect('explanations:pending_approvals')

    return render(request, 'explanations/review.html', {'exp': exp, 'locked': locked})

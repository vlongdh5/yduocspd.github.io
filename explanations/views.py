from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Explanation, ExplanationReason
from attendance.models import AttendanceRecord


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

    qs = Explanation.objects.filter(status=Explanation.Status.PENDING).select_related(
        'employee__department', 'record', 'reason'
    )
    if request.user.is_tbp and not request.user.is_hr:
        dept = request.user.managed_departments.first()
        if dept:
            qs = qs.filter(employee__department=dept)

    return render(request, 'explanations/pending_approvals.html', {'explanations': qs})


@login_required
def review_explanation(request, pk):
    if not (request.user.is_tbp or request.user.is_hr):
        return redirect('attendance:my_attendance')

    exp = get_object_or_404(Explanation, pk=pk)

    if request.method == 'POST':
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

    return render(request, 'explanations/review.html', {'exp': exp})

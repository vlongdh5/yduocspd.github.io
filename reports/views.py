import os
import tempfile
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.contrib import messages
from django.db.models import Q
from attendance.models import AttendanceUpload, AttendanceRecord
from explanations.models import Explanation
from .calculator import calculate_month
from .exporter import export_calculation_excel


def _explanation_summary(month):
    """
    Returns (not_submitted, pending, all_error_records) for the given month.

    not_submitted: records with errors where the employee has not filled in any reason yet
    pending: records where at least one side is pending TBP review
    all_error_records: all error records annotated with their explanation
    """
    error_records = (
        AttendanceRecord.objects
        .filter(upload__month=month, status='error')
        .select_related('employee__department', 'explanation__ci_reason', 'explanation__co_reason')
        .order_by('employee__code', 'date')
    )

    not_submitted = []
    pending = []
    reviewed = []

    for record in error_records:
        exp = getattr(record, 'explanation', None)
        needs_ci = record.has_ci_issue
        needs_co = record.has_co_issue

        ci_submitted = exp and exp.ci_reason_id is not None
        co_submitted = exp and exp.co_reason_id is not None

        fully_submitted = (
            (not needs_ci or ci_submitted) and
            (not needs_co or co_submitted)
        )

        if not fully_submitted:
            not_submitted.append(record)
            continue

        has_pending = (
            (needs_ci and exp.ci_status == Explanation.Status.PENDING) or
            (needs_co and exp.co_status == Explanation.Status.PENDING)
        )

        if has_pending:
            pending.append(record)
        else:
            reviewed.append(record)

    return not_submitted, pending, reviewed


@login_required
def calculate_view(request):
    if not request.user.is_hr:
        return redirect('attendance:my_attendance')

    months = list(
        AttendanceUpload.objects.filter(status='done')
        .values_list('month', flat=True).distinct().order_by('-month')
    )

    results = None
    selected_month = request.GET.get('month') or (months[0] if months else None)
    active_tab = request.GET.get('tab', 'calculate')

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_month = request.POST.get('month')

        if action == 'calculate':
            try:
                results = calculate_month(month=selected_month, calculated_by=request.user)
                messages.success(request, f'Đã tính công cho {len(results)} nhân viên.')
            except ValueError as e:
                messages.error(request, str(e))
            active_tab = 'calculate'

        elif action == 'export':
            tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
            tmp_path = tmp.name
            tmp.close()
            try:
                export_calculation_excel(selected_month, tmp_path)
                response = FileResponse(
                    open(tmp_path, 'rb'),
                    as_attachment=True,
                    filename=f'bang_tong_hop_cong_{selected_month}.xlsx'
                )
                response['X-Accel-Buffering'] = 'no'
                os.unlink(tmp_path)
                return response
            except Exception:
                os.unlink(tmp_path)
                raise

    not_submitted, pending, reviewed = [], [], []
    if selected_month:
        not_submitted, pending, reviewed = _explanation_summary(selected_month)

    return render(request, 'reports/calculate.html', {
        'months': months,
        'results': results,
        'selected_month': selected_month,
        'active_tab': active_tab,
        'not_submitted': not_submitted,
        'pending': pending,
        'reviewed': reviewed,
        'count_not_submitted': len(not_submitted),
        'count_pending': len(pending),
        'count_all_errors': len(not_submitted) + len(pending) + len(reviewed),
    })

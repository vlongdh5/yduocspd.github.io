from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import AttendanceRecord, AttendanceUpload


def _rollback_leave_for_month(month):
    """Roll back LeaveBalance.used_hours based on AttendanceCalculation.leave_hours
    for the given month. Must be called BEFORE deleting AttendanceCalculation records."""
    from reports.models import AttendanceCalculation
    from employees.models import LeaveBalance

    year = int(month[:4])
    for calc in AttendanceCalculation.objects.filter(month=month).select_related('employee'):
        if float(calc.leave_hours) <= 0:
            continue
        try:
            lb = LeaveBalance.objects.get(employee=calc.employee, year=year)
            lb.used_hours = max(Decimal('0'), lb.used_hours - calc.leave_hours)
            lb.save()
        except LeaveBalance.DoesNotExist:
            pass


def _rollback_compensatory_for_uploads(upload_ids):
    """Before cascade-deleting uploads, roll back PROVISIONAL and DEBIT compensatory
    transactions for affected employees within the month's date range.

    PROVISIONAL: created when employee submits explanation with use_compensatory.
    DEBIT: created by calculate_month; must also be rolled back so re-calculating
    after a re-upload starts from a clean state.

    Filters by employee+date range (not via explanation join) so orphaned transactions
    — where explanation was already SET_NULL — are also caught.
    """
    if not upload_ids:
        return
    import calendar
    from datetime import date as _date
    from django.db.models import Q
    from employees.models import CompensatoryBalance, CompensatoryTransaction

    emp_ids = list(
        AttendanceRecord.objects.filter(upload_id__in=upload_ids)
        .values_list('employee_id', flat=True).distinct()
    )
    months = list(
        AttendanceUpload.objects.filter(pk__in=upload_ids)
        .values_list('month', flat=True).distinct()
    )
    if not emp_ids or not months:
        return

    date_q = Q()
    for m in months:
        y, mo = m.split('-')
        first = _date(int(y), int(mo), 1)
        last = _date(int(y), int(mo), calendar.monthrange(int(y), int(mo))[1])
        date_q |= Q(date__range=(first, last))

    tx_qs = CompensatoryTransaction.objects.filter(
        transaction_type__in=[
            CompensatoryTransaction.Type.PROVISIONAL,
            CompensatoryTransaction.Type.DEBIT,
        ],
        employee_id__in=emp_ids,
    ).filter(date_q)

    by_employee = {}
    for tx in tx_qs:
        by_employee.setdefault(tx.employee_id, Decimal('0'))
        by_employee[tx.employee_id] += tx.hours
    for emp_id, total in by_employee.items():
        try:
            bal = CompensatoryBalance.objects.get(employee_id=emp_id)
            bal.used_hours = max(Decimal('0'), bal.used_hours - total)
            bal.save()
        except CompensatoryBalance.DoesNotExist:
            pass
    tx_qs.delete()


def _is_fully_submitted(record):
    """True if all CI/CO issues on this error record have been submitted."""
    exp = getattr(record, 'explanation', None)
    if record.has_ci_issue and (exp is None or exp.ci_reason_id is None):
        return False
    if record.has_co_issue and (exp is None or exp.co_reason_id is None):
        return False
    return True


@login_required
def my_attendance(request):
    from datetime import date
    try:
        employee = request.user.employee_profile
    except Exception:
        return render(request, 'attendance/no_profile.html')

    months = (AttendanceRecord.objects
              .filter(employee=employee)
              .values_list('upload__month', flat=True)
              .distinct().order_by('-upload__month'))

    # Default: tháng gần nhất có dữ liệu của nhân viên này
    default_month = months[0] if months else date.today().strftime('%Y-%m')
    month = request.GET.get('month', default_month)

    records = (AttendanceRecord.objects
               .filter(employee=employee, upload__month=month)
               .select_related('explanation')
               .order_by('date'))

    # Tổng số ngày lỗi chưa nộp đủ giải trình (toàn bộ tháng)
    error_records = (AttendanceRecord.objects
                     .filter(employee=employee, status='error')
                     .select_related('explanation'))
    pending_count = sum(
        1 for r in error_records
        if not _is_fully_submitted(r)
    )

    return render(request, 'attendance/my_attendance.html', {
        'records': records,
        'month': month,
        'months': months,
        'employee': employee,
        'pending_count': pending_count,
    })


def _do_process(request, upload):
    from .upload_processor import process_upload
    from .parser import parse_attendance_excel, InvalidAttendanceFile
    try:
        rows = parse_attendance_excel(upload.file.path)
        process_upload(upload, rows)
        messages.success(
            request,
            f'Upload thành công: {upload.total_records} bản ghi, {upload.error_records} lỗi.'
        )
    except InvalidAttendanceFile as e:
        upload.delete()
        messages.error(request, str(e))
        return False
    except Exception as e:
        upload.status = AttendanceUpload.Status.ERROR
        upload.notes = str(e)
        upload.save()
        messages.error(request, f'Lỗi xử lý file: {e}')
    return True


@login_required
def upload_attendance(request):
    if not request.user.is_hr:
        return redirect('attendance:my_attendance')

    from .forms import AttendanceUploadForm
    from explanations.models import Explanation

    recent_uploads = AttendanceUpload.objects.order_by('-uploaded_at')[:10]

    # Bước 2a: HR xác nhận ghi đè
    if request.method == 'POST' and 'confirm_overwrite' in request.POST:
        from reports.models import AttendanceCalculation
        upload = get_object_or_404(AttendanceUpload, pk=request.POST.get('pending_upload_pk'))
        month = upload.month
        old_upload_ids = list(
            AttendanceUpload.objects.filter(month=month).exclude(pk=upload.pk).values_list('pk', flat=True)
        )
        # Roll back leave balance from calculations before deleting them
        _rollback_leave_for_month(month)
        # Roll back provisional and debit compensatory transactions before cascade-delete
        _rollback_compensatory_for_uploads(old_upload_ids)
        # Cascade: AttendanceUpload → AttendanceRecord → Explanation
        AttendanceUpload.objects.filter(pk__in=old_upload_ids).delete()
        # Không cascade: xóa tính công cũ của tháng này
        AttendanceCalculation.objects.filter(month=month).delete()
        ok = _do_process(request, upload)
        if not ok:
            return render(request, 'attendance/upload.html', {'form': AttendanceUploadForm(), 'recent_uploads': recent_uploads})
        return redirect('attendance:upload_detail', pk=upload.pk)

    # Bước 2b: HR huỷ
    if request.method == 'POST' and 'cancel_overwrite' in request.POST:
        upload = get_object_or_404(AttendanceUpload, pk=request.POST.get('pending_upload_pk'))
        upload.delete()
        messages.info(request, 'Đã huỷ upload.')
        return redirect('attendance:upload')

    if request.method == 'POST':
        form = AttendanceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.uploaded_by = request.user
            upload.save()

            existing = AttendanceUpload.objects.filter(month=upload.month).exclude(pk=upload.pk)
            if existing.exists():
                from reports.models import AttendanceCalculation
                existing_records = AttendanceRecord.objects.filter(upload__in=existing).count()
                existing_explanations = Explanation.objects.filter(record__upload__in=existing).count()
                existing_calculations = AttendanceCalculation.objects.filter(month=upload.month).count()
                return render(request, 'attendance/upload_confirm.html', {
                    'upload': upload,
                    'existing_records': existing_records,
                    'existing_explanations': existing_explanations,
                    'existing_calculations': existing_calculations,
                })

            ok = _do_process(request, upload)
            if not ok:
                return render(request, 'attendance/upload.html', {'form': AttendanceUploadForm(), 'recent_uploads': recent_uploads})
            return redirect('attendance:upload_detail', pk=upload.pk)
    else:
        form = AttendanceUploadForm()

    return render(request, 'attendance/upload.html', {'form': form, 'recent_uploads': recent_uploads})


@login_required
def upload_detail(request, pk):
    if not request.user.is_hr:
        return redirect('attendance:my_attendance')
    upload = get_object_or_404(AttendanceUpload, pk=pk)
    error_records = upload.records.filter(status='error').select_related('employee')
    return render(request, 'attendance/upload_detail.html', {
        'upload': upload, 'error_records': error_records
    })

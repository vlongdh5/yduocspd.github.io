from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import AttendanceRecord, AttendanceUpload


@login_required
def my_attendance(request):
    from datetime import date
    month = request.GET.get('month', date.today().strftime('%Y-%m'))
    try:
        employee = request.user.employee_profile
    except Exception:
        return render(request, 'attendance/no_profile.html')

    records = AttendanceRecord.objects.filter(
        employee=employee,
        upload__month=month
    ).select_related('explanation').order_by('date')

    months = AttendanceUpload.objects.values_list('month', flat=True).distinct().order_by('-month')

    return render(request, 'attendance/my_attendance.html', {
        'records': records,
        'month': month,
        'months': months,
        'employee': employee,
    })


@login_required
def upload_attendance(request):
    if not request.user.is_hr:
        return redirect('attendance:my_attendance')

    from .forms import AttendanceUploadForm
    from .upload_processor import process_upload
    from .parser import parse_attendance_excel, InvalidAttendanceFile

    recent_uploads = AttendanceUpload.objects.order_by('-uploaded_at')[:10]

    if request.method == 'POST':
        form = AttendanceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.uploaded_by = request.user
            upload.save()
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
                return render(request, 'attendance/upload.html', {'form': form, 'recent_uploads': recent_uploads})
            except Exception as e:
                upload.status = AttendanceUpload.Status.ERROR
                upload.notes = str(e)
                upload.save()
                messages.error(request, f'Lỗi xử lý file: {e}')
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

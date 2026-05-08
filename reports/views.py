import os
import tempfile
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.contrib import messages
from attendance.models import AttendanceUpload
from .calculator import calculate_month
from .exporter import export_calculation_excel


@login_required
def calculate_view(request):
    if not request.user.is_hr:
        return redirect('attendance:my_attendance')

    months = AttendanceUpload.objects.filter(
        status='done'
    ).values_list('month', flat=True).distinct().order_by('-month')

    results = None
    selected_month = None

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_month = request.POST.get('month')

        if action == 'calculate':
            results = calculate_month(month=selected_month, calculated_by=request.user)
            messages.success(request, f'Đã tính công cho {len(results)} nhân viên.')

        elif action == 'export':
            tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
            tmp.close()
            export_calculation_excel(selected_month, tmp.name)
            response = FileResponse(
                open(tmp.name, 'rb'),
                as_attachment=True,
                filename=f'bang_tong_hop_cong_{selected_month}.xlsx'
            )
            os.unlink(tmp.name)
            return response

    return render(request, 'reports/calculate.html', {
        'months': months, 'results': results, 'selected_month': selected_month
    })

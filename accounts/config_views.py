from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .otp import is_otp_enabled, set_otp_enabled
from attendance.models import ErrorType
from explanations.models import ExplanationReason


@login_required
def config_view(request):
    if not request.user.is_superuser:
        return redirect('attendance:my_attendance')

    if request.method == 'POST':
        otp_enabled = request.POST.get('otp_enabled') == 'on'
        set_otp_enabled(otp_enabled)
        messages.success(request, 'Đã lưu cấu hình.')
        return redirect('accounts:config')

    context = {
        'otp_enabled': is_otp_enabled(),
        'error_types': ErrorType.objects.all().order_by('code'),
        'explanation_reasons': ExplanationReason.objects.all().order_by('order', 'name'),
    }
    return render(request, 'accounts/config.html', context)

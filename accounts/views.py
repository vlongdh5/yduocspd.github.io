from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.views import View
from django.contrib import messages
from django.core.cache import cache
from .forms import LoginForm, OTPVerifyForm
from .otp import is_otp_enabled, TOTPManager
from .models import User

_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_LOCKOUT_SECONDS = 900   # 15 phút
_OTP_MAX_ATTEMPTS = 5
_OTP_LOCKOUT_SECONDS = 600     # 10 phút


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '')


def _is_locked(key):
    return cache.get(key, 0) >= _LOGIN_MAX_ATTEMPTS


def _record_failure(key, ttl):
    count = cache.get(key, 0) + 1
    cache.set(key, count, ttl)
    return count


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('/')
        return render(request, self.template_name, {'form': LoginForm()})

    def post(self, request):
        ip = _client_ip(request)
        lock_key = f'login_lock_{ip}'

        if _is_locked(lock_key):
            messages.error(request, 'Đăng nhập bị tạm khóa 15 phút do thử sai quá nhiều lần.')
            return render(request, self.template_name, {'form': LoginForm(), 'locked': True})

        form = LoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        user = authenticate(
            request,
            username=form.cleaned_data['email'],
            password=form.cleaned_data['password']
        )
        if user is None:
            count = _record_failure(lock_key, _LOGIN_LOCKOUT_SECONDS)
            remaining = max(0, _LOGIN_MAX_ATTEMPTS - count)
            if remaining:
                messages.error(request, f'Email hoặc mật khẩu không đúng. Còn {remaining} lần thử.')
            else:
                messages.error(request, 'Đăng nhập bị tạm khóa 15 phút do thử sai quá nhiều lần.')
            return render(request, self.template_name, {'form': form})

        cache.delete(lock_key)  # reset on success

        if is_otp_enabled():
            request.session['pre_otp_user_id'] = user.pk
            if user.otp_method == 'totp' and user.totp_secret:
                request.session['otp_method'] = 'totp'
            else:
                _send_email_otp(request, user)
            return redirect('accounts:verify_otp')

        login(request, user)
        return redirect(request.GET.get('next', '/'))


def _send_email_otp(request, user):
    from django_otp.plugins.otp_email.models import EmailDevice
    device, _ = EmailDevice.objects.get_or_create(user=user, name='default')
    device.generate_challenge()
    request.session['otp_method'] = 'email'


class OTPVerifyView(View):
    template_name = 'accounts/otp_verify.html'

    def get(self, request):
        if 'pre_otp_user_id' not in request.session:
            return redirect('accounts:login')
        method = request.session.get('otp_method', 'email')
        return render(request, self.template_name, {'form': OTPVerifyForm(), 'method': method})

    def post(self, request):
        if 'pre_otp_user_id' not in request.session:
            return redirect('accounts:login')

        ip = _client_ip(request)
        user_id = request.session['pre_otp_user_id']
        otp_key = f'otp_lock_{ip}_{user_id}'

        if cache.get(otp_key, 0) >= _OTP_MAX_ATTEMPTS:
            messages.error(request, 'OTP bị tạm khóa 10 phút do thử sai quá nhiều lần.')
            del request.session['pre_otp_user_id']
            return redirect('accounts:login')

        form = OTPVerifyForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        user = User.objects.get(pk=user_id)
        code = form.cleaned_data['otp_code']
        method = request.session.get('otp_method', 'email')

        verified = False
        if method == 'totp':
            verified = TOTPManager.verify(user.totp_secret, code)
        else:
            from django_otp.plugins.otp_email.models import EmailDevice
            try:
                device = EmailDevice.objects.get(user=user, name='default')
                verified = device.verify_token(code)
            except EmailDevice.DoesNotExist:
                pass

        if verified:
            cache.delete(otp_key)
            del request.session['pre_otp_user_id']
            login(request, user)
            return redirect(request.GET.get('next', '/'))

        _record_failure(otp_key, _OTP_LOCKOUT_SECONDS)
        messages.error(request, 'Mã OTP không đúng hoặc đã hết hạn.')
        return render(request, self.template_name, {'form': form, 'method': method})


class SetupTOTPView(View):
    template_name = 'accounts/setup_totp.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.totp_secret:
            request.user.totp_secret = TOTPManager.generate_secret()
            request.user.save()
        qr = TOTPManager.generate_qr_code_base64(request.user.totp_secret, request.user.email)
        return render(request, self.template_name, {'qr_code': qr})

    def post(self, request):
        code = request.POST.get('code', '')
        if TOTPManager.verify(request.user.totp_secret, code):
            request.user.otp_method = 'totp'
            request.user.save()
            messages.success(request, 'Đã kích hoạt Google Authenticator.')
            return redirect('/')
        messages.error(request, 'Mã không đúng, vui lòng thử lại.')
        qr = TOTPManager.generate_qr_code_base64(request.user.totp_secret, request.user.email)
        return render(request, self.template_name, {'qr_code': qr})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')

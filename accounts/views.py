from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.views import View
from django.contrib import messages
from .forms import LoginForm, OTPVerifyForm
from .otp import is_otp_enabled, TOTPManager
from .models import User


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('/')
        return render(request, self.template_name, {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        user = authenticate(
            request,
            username=form.cleaned_data['email'],
            password=form.cleaned_data['password']
        )
        if user is None:
            messages.error(request, 'Email hoặc mật khẩu không đúng.')
            return render(request, self.template_name, {'form': form})

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
        form = OTPVerifyForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        user_id = request.session['pre_otp_user_id']
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
            del request.session['pre_otp_user_id']
            login(request, user)
            return redirect(request.GET.get('next', '/'))

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

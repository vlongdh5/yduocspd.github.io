# HR Attendance Management System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Django full-stack web app for HR attendance management — upload, error detection, employee explanation, TBP approval, leave calculation, and Excel export.

**Architecture:** Django 5.x full-stack with Django Templates + Bootstrap 5 for responsive UI. Custom User model with email auth + OTP (email or Google Authenticator). SQLite for dev, PostgreSQL-ready for production.

**Tech Stack:** Django 5, django-otp, pyotp, qrcode, openpyxl, Bootstrap 5, whitenoise, gunicorn, pytest-django

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `hrms/settings/base.py`
- Create: `hrms/settings/development.py`
- Create: `hrms/settings/production.py`
- Create: `hrms/__init__.py`
- Create: `hrms/urls.py`
- Create: `hrms/wsgi.py`
- Create: `manage.py`
- Create: `.env.example`
- Create: `.gitignore`

**Step 1: Create virtual environment and install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Step 2: Create requirements.txt**

```
Django>=5.0,<6.0
django-otp==1.5.4
pyotp==2.9.0
qrcode[pil]==7.4.2
openpyxl==3.1.2
whitenoise==6.7.0
gunicorn==22.0.0
psycopg2-binary==2.9.9
python-dotenv==1.0.1
pytest==8.3.2
pytest-django==4.9.0
```

**Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

**Step 4: Create Django project structure**

```bash
django-admin startproject hrms .
```

**Step 5: Create settings package**

```bash
mkdir hrms/settings
mv hrms/settings.py hrms/settings/base.py
touch hrms/settings/__init__.py hrms/settings/development.py hrms/settings/production.py
```

**Step 6: Write hrms/settings/base.py**

```python
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_otp',
    'django_otp.plugins.otp_email',
    'django_otp.plugins.otp_totp',
    'accounts',
    'employees',
    'attendance',
    'explanations',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hrms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hrms.wsgi.application'

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@company.com')

OTP_EMAIL_SUBJECT = 'Mã OTP đăng nhập HR System'
OTP_EMAIL_BODY_TEMPLATE_PATH = 'accounts/otp_email.txt'
OTP_TOTP_ISSUER = 'HR System'
```

**Step 7: Write hrms/settings/development.py**

```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

**Step 8: Write hrms/settings/production.py**

```python
from .base import *
import os

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

**Step 9: Update manage.py to use development settings**

Edit `manage.py` to set default settings module:
```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms.settings.development')
```

**Step 10: Create pytest.ini**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = hrms.settings.development
python_files = tests/test_*.py
python_classes = Test*
python_functions = test_*
```

**Step 11: Create .env.example**

```
SECRET_KEY=your-secret-key-here
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@company.com
ALLOWED_HOSTS=yourdomain.com
DB_NAME=hrms
DB_USER=hrms
DB_PASSWORD=password
DB_HOST=localhost
```

**Step 12: Create .gitignore**

```
.venv/
__pycache__/
*.pyc
db.sqlite3
.env
media/
staticfiles/
*.log
```

**Step 13: Create app directories**

```bash
python manage.py startapp accounts
python manage.py startapp employees
python manage.py startapp attendance
python manage.py startapp explanations
python manage.py startapp reports
mkdir -p templates/base templates/accounts templates/employees templates/attendance templates/explanations templates/reports
mkdir -p static/css static/js static/images
mkdir -p media
```

**Step 14: Verify setup runs**

```bash
python manage.py check
```

Expected: "System check identified no issues (0 silenced)."

**Step 15: Commit**

```bash
git add -A
git commit -m "feat: initial Django project setup"
```

---

## Task 2: Custom User Model & Role System

**Files:**
- Create: `accounts/models.py`
- Create: `accounts/tests/test_user_model.py`
- Modify: `accounts/admin.py`

**Step 1: Write failing tests**

```python
# accounts/tests/test_user_model.py
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_create_user_with_email():
    user = User.objects.create_user(email='test@example.com', password='pass123')
    assert user.email == 'test@example.com'
    assert user.username == 'test@example.com'
    assert user.check_password('pass123')

@pytest.mark.django_db
def test_user_roles():
    hr = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    emp = User.objects.create_user(email='emp@example.com', password='pass', role=User.Role.EMPLOYEE)
    tbp = User.objects.create_user(email='tbp@example.com', password='pass', role=User.Role.TBP)
    assert hr.is_hr
    assert emp.is_employee
    assert tbp.is_tbp

@pytest.mark.django_db
def test_user_email_required():
    with pytest.raises(ValueError):
        User.objects.create_user(email='', password='pass')

@pytest.mark.django_db
def test_user_can_have_multiple_roles():
    user = User.objects.create_user(
        email='tbpemp@example.com', password='pass',
        role=User.Role.TBP
    )
    user.extra_roles = [User.Role.EMPLOYEE]
    user.save()
    assert user.is_tbp
    assert user.is_employee
```

**Step 2: Run tests to verify they fail**

```bash
mkdir -p accounts/tests && touch accounts/tests/__init__.py
pytest accounts/tests/test_user_model.py -v
```

Expected: FAIL — `accounts.models` not defined

**Step 3: Write accounts/models.py**

```python
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.HR)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        HR = 'HR', 'HR'
        EMPLOYEE = 'EMPLOYEE', 'Nhân viên'
        TBP = 'TBP', 'Trưởng bộ phận'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    extra_roles = models.JSONField(default=list, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def is_hr(self):
        return self.role == self.Role.HR

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE or self.Role.EMPLOYEE in self.extra_roles

    @property
    def is_tbp(self):
        return self.role == self.Role.TBP or self.Role.TBP in self.extra_roles
```

**Step 4: Run tests**

```bash
python manage.py makemigrations accounts
pytest accounts/tests/test_user_model.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add accounts/
git commit -m "feat: custom User model with email auth and role system"
```

---

## Task 3: Employee & Department Models

**Files:**
- Create: `employees/models.py`
- Create: `employees/tests/test_models.py`
- Create: `employees/admin.py`

**Step 1: Write failing tests**

```python
# employees/tests/test_models.py
import pytest
from employees.models import Department, Employee
from accounts.models import User

@pytest.mark.django_db
def test_create_department():
    dept = Department.objects.create(name='Kinh doanh')
    assert str(dept) == 'Kinh doanh'

@pytest.mark.django_db
def test_department_has_manager():
    user = User.objects.create_user(email='tbp@example.com', password='pass', role=User.Role.TBP)
    dept = Department.objects.create(name='Kinh doanh', manager=user)
    assert dept.manager == user

@pytest.mark.django_db
def test_create_employee():
    user = User.objects.create_user(email='emp@example.com', password='pass')
    dept = Department.objects.create(name='Kinh doanh')
    emp = Employee.objects.create(
        user=user, code='NV001', full_name='Nguyen Van A',
        department=dept, position='Sales'
    )
    assert emp.code == 'NV001'
    assert emp.is_active is True
    assert str(emp) == 'NV001 - Nguyen Van A'

@pytest.mark.django_db
def test_employee_code_unique():
    user1 = User.objects.create_user(email='emp1@example.com', password='pass')
    user2 = User.objects.create_user(email='emp2@example.com', password='pass')
    dept = Department.objects.create(name='Kinh doanh')
    Employee.objects.create(user=user1, code='NV001', full_name='A', department=dept)
    with pytest.raises(Exception):
        Employee.objects.create(user=user2, code='NV001', full_name='B', department=dept)
```

**Step 2: Run tests to verify fail**

```bash
mkdir -p employees/tests && touch employees/tests/__init__.py
pytest employees/tests/test_models.py -v
```

Expected: FAIL

**Step 3: Write employees/models.py**

```python
from django.db import models
from accounts.models import User


class Department(models.Model):
    name = models.CharField(max_length=100)
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_departments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Phòng ban'
        verbose_name_plural = 'Phòng ban'


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    code = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='employees')
    position = models.CharField(max_length=100, blank=True)
    start_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.code} - {self.full_name}'

    class Meta:
        verbose_name = 'Nhân viên'
        verbose_name_plural = 'Nhân viên'
        ordering = ['code']
```

**Step 4: Migrate and run tests**

```bash
python manage.py makemigrations employees
python manage.py migrate
pytest employees/tests/test_models.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add employees/
git commit -m "feat: Employee and Department models"
```

---

## Task 4: OTP System (Email OTP + Google Authenticator)

**Files:**
- Create: `accounts/otp.py`
- Create: `accounts/tests/test_otp.py`
- Modify: `employees/models.py` — add `otp_enabled` system config

**Step 1: Write failing tests**

```python
# accounts/tests/test_otp.py
import pytest
from unittest.mock import patch
from accounts.otp import TOTPManager, is_otp_enabled, set_otp_enabled

def test_totp_generate_secret():
    secret = TOTPManager.generate_secret()
    assert len(secret) == 32

def test_totp_generate_provisioning_uri():
    secret = TOTPManager.generate_secret()
    uri = TOTPManager.get_provisioning_uri(secret, 'test@example.com')
    assert 'test@example.com' in uri
    assert 'HR System' in uri

def test_totp_verify_valid_code():
    import pyotp
    secret = TOTPManager.generate_secret()
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    assert TOTPManager.verify(secret, current_code) is True

def test_totp_verify_invalid_code():
    secret = TOTPManager.generate_secret()
    assert TOTPManager.verify(secret, '000000') is False

def test_otp_enabled_default_false():
    assert is_otp_enabled() is False

@pytest.mark.django_db
def test_otp_toggle():
    set_otp_enabled(True)
    assert is_otp_enabled() is True
    set_otp_enabled(False)
    assert is_otp_enabled() is False
```

**Step 2: Run tests to verify fail**

```bash
pytest accounts/tests/test_otp.py -v
```

Expected: FAIL

**Step 3: Write accounts/otp.py**

```python
import pyotp
import qrcode
import io
import base64
from django.core.cache import cache

TOTP_ISSUER = 'HR System'
OTP_ENABLED_CACHE_KEY = 'otp_system_enabled'


class TOTPManager:
    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(secret: str, email: str) -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=TOTP_ISSUER)

    @staticmethod
    def verify(secret: str, code: str) -> bool:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    @staticmethod
    def generate_qr_code_base64(secret: str, email: str) -> str:
        uri = TOTPManager.get_provisioning_uri(secret, email)
        img = qrcode.make(uri)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()


def is_otp_enabled() -> bool:
    from accounts.models import SystemConfig
    try:
        return SystemConfig.get('otp_enabled', False)
    except Exception:
        return False


def set_otp_enabled(enabled: bool):
    from accounts.models import SystemConfig
    SystemConfig.set('otp_enabled', enabled)
```

**Step 4: Add SystemConfig model to accounts/models.py**

```python
class SystemConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value):
        obj, _ = cls.objects.get_or_create(key=key)
        obj.value = value
        obj.save()

    class Meta:
        verbose_name = 'Cấu hình hệ thống'
```

**Step 5: Add TOTP secret to User model**

```python
# in accounts/models.py User class:
totp_secret = models.CharField(max_length=64, blank=True)
otp_method = models.CharField(
    max_length=10,
    choices=[('email', 'Email OTP'), ('totp', 'Google Authenticator')],
    default='email'
)
```

**Step 6: Migrate and run tests**

```bash
python manage.py makemigrations accounts
python manage.py migrate
pytest accounts/tests/test_otp.py -v
```

Expected: All PASS

**Step 7: Commit**

```bash
git add accounts/
git commit -m "feat: OTP system with email OTP and Google Authenticator TOTP"
```

---

## Task 5: Login Flow with OTP

**Files:**
- Create: `accounts/views.py`
- Create: `accounts/forms.py`
- Create: `accounts/urls.py`
- Create: `templates/accounts/login.html`
- Create: `templates/accounts/otp_verify.html`
- Create: `templates/accounts/setup_totp.html`
- Create: `templates/accounts/otp_email.txt`
- Create: `accounts/tests/test_views.py`

**Step 1: Write failing tests**

```python
# accounts/tests/test_views.py
import pytest
from django.test import Client
from django.urls import reverse
from accounts.models import User

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def user(db):
    return User.objects.create_user(email='test@example.com', password='testpass123')

def test_login_page_loads(client):
    response = client.get(reverse('accounts:login'))
    assert response.status_code == 200

def test_login_with_valid_credentials_no_otp(client, user):
    from accounts.otp import set_otp_enabled
    set_otp_enabled(False)
    response = client.post(reverse('accounts:login'), {
        'email': 'test@example.com',
        'password': 'testpass123'
    })
    assert response.status_code == 302

def test_login_with_invalid_credentials(client, user):
    response = client.post(reverse('accounts:login'), {
        'email': 'test@example.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 200
    assert 'error' in response.context or b'error' in response.content.lower()

def test_logout(client, user):
    client.force_login(user)
    response = client.post(reverse('accounts:logout'))
    assert response.status_code == 302
```

**Step 2: Run tests to verify fail**

```bash
mkdir -p accounts/tests
pytest accounts/tests/test_views.py -v
```

Expected: FAIL

**Step 3: Write accounts/forms.py**

```python
from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mật khẩu'})
    )


class OTPVerifyForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6, min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': '000000',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
        })
    )
```

**Step 4: Write accounts/views.py**

```python
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
                return redirect('accounts:verify_otp')
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
        return render(request, self.template_name, {
            'form': OTPVerifyForm(), 'method': method
        })

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
```

**Step 5: Write accounts/urls.py**

```python
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('otp/verify/', views.OTPVerifyView.as_view(), name='verify_otp'),
    path('otp/setup-totp/', views.SetupTOTPView.as_view(), name='setup_totp'),
]
```

**Step 6: Update hrms/urls.py**

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Step 7: Create base template — templates/base/base.html**

```html
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}HR System{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% if user.is_authenticated %}
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand fw-bold" href="/"><i class="bi bi-people-fill"></i> HR System</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/attendance/"><i class="bi bi-calendar-check"></i> Chấm công</a>
                    </li>
                    {% if user.is_tbp %}
                    <li class="nav-item">
                        <a class="nav-link" href="/explanations/pending/"><i class="bi bi-check2-circle"></i> Duyệt giải trình</a>
                    </li>
                    {% endif %}
                    {% if user.is_hr %}
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown"><i class="bi bi-gear"></i> HR</a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="/attendance/upload/">Upload chấm công</a></li>
                            <li><a class="dropdown-item" href="/reports/calculate/">Tính công</a></li>
                            <li><a class="dropdown-item" href="/employees/">Quản lý nhân viên</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="/accounts/config/">Cấu hình</a></li>
                        </ul>
                    </li>
                    {% endif %}
                </ul>
                <ul class="navbar-nav">
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
                            <i class="bi bi-person-circle"></i> {{ user.email }}
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="/accounts/otp/setup-totp/">Cài Google Authenticator</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li>
                                <form method="post" action="/accounts/logout/">
                                    {% csrf_token %}
                                    <button type="submit" class="dropdown-item text-danger">Đăng xuất</button>
                                </form>
                            </li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    {% endif %}

    <div class="container-fluid py-4">
        {% for message in messages %}
        <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        {% endfor %}
        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

**Step 8: Create templates/accounts/login.html**

```html
{% extends "base/base.html" %}
{% block title %}Đăng nhập — HR System{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-12 col-sm-8 col-md-5 col-lg-4">
        <div class="card shadow-sm mt-5">
            <div class="card-body p-4">
                <h4 class="card-title text-center mb-4">
                    <i class="bi bi-people-fill text-primary"></i> HR System
                </h4>
                <form method="post">
                    {% csrf_token %}
                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        {{ form.email }}
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Mật khẩu</label>
                        {{ form.password }}
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Đăng nhập</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

**Step 9: Create templates/accounts/otp_verify.html**

```html
{% extends "base/base.html" %}
{% block title %}Xác thực OTP{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-12 col-sm-8 col-md-5 col-lg-4">
        <div class="card shadow-sm mt-5">
            <div class="card-body p-4 text-center">
                <h5 class="mb-3">
                    {% if method == 'totp' %}
                    <i class="bi bi-phone"></i> Nhập mã từ Google Authenticator
                    {% else %}
                    <i class="bi bi-envelope"></i> Nhập mã OTP từ email
                    {% endif %}
                </h5>
                <form method="post">
                    {% csrf_token %}
                    <div class="mb-3">{{ form.otp_code }}</div>
                    <button type="submit" class="btn btn-primary w-100">Xác nhận</button>
                </form>
                <a href="{% url 'accounts:login' %}" class="d-block mt-3 text-muted small">Quay lại đăng nhập</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

**Step 10: Run tests**

```bash
pytest accounts/tests/test_views.py -v
```

Expected: All PASS

**Step 11: Commit**

```bash
git add accounts/ templates/ hrms/urls.py
git commit -m "feat: login flow with OTP support"
```

---

## Task 6: Attendance Upload & Excel Parsing

**Files:**
- Create: `attendance/models.py`
- Create: `attendance/parser.py`
- Create: `attendance/tests/test_parser.py`
- Create: `attendance/tests/fixtures/sample_attendance.xlsx` (created programmatically)

**Step 1: Write failing tests**

```python
# attendance/tests/test_parser.py
import pytest
from datetime import date, time
from attendance.parser import parse_attendance_excel, AttendanceRow
from openpyxl import Workbook
import tempfile, os

def make_sample_excel(rows):
    wb = Workbook()
    ws = wb.active
    ws.append(['Mã NV', 'Họ tên', 'Ngày', 'Giờ vào', 'Giờ ra', 'Mã ca'])
    for row in rows:
        ws.append(row)
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(tmp.name)
    return tmp.name

def test_parse_valid_rows():
    path = make_sample_excel([
        ['NV001', 'Nguyen Van A', '2026-05-01', '08:00', '17:00', 'HC'],
        ['NV002', 'Tran Thi B', '2026-05-01', '08:05', '17:10', 'HC'],
    ])
    rows = parse_attendance_excel(path)
    os.unlink(path)
    assert len(rows) == 2
    assert rows[0].employee_code == 'NV001'
    assert rows[0].check_in == time(8, 0)
    assert rows[0].check_out == time(17, 0)
    assert rows[0].shift_code == 'HC'

def test_parse_missing_checkin():
    path = make_sample_excel([
        ['NV001', 'Nguyen Van A', '2026-05-01', None, '17:00', 'HC'],
    ])
    rows = parse_attendance_excel(path)
    os.unlink(path)
    assert rows[0].check_in is None
    assert rows[0].check_out == time(17, 0)

def test_parse_empty_row_skipped():
    path = make_sample_excel([
        ['NV001', 'Nguyen Van A', '2026-05-01', '08:00', '17:00', 'HC'],
        [None, None, None, None, None, None],
    ])
    rows = parse_attendance_excel(path)
    os.unlink(path)
    assert len(rows) == 1
```

**Step 2: Run tests to verify fail**

```bash
mkdir -p attendance/tests && touch attendance/tests/__init__.py
pytest attendance/tests/test_parser.py -v
```

Expected: FAIL

**Step 3: Write attendance/parser.py**

```python
from dataclasses import dataclass
from datetime import date, time, datetime
from typing import Optional
from openpyxl import load_workbook


@dataclass
class AttendanceRow:
    employee_code: str
    employee_name: str
    date: date
    check_in: Optional[time]
    check_out: Optional[time]
    shift_code: str


def _parse_time(value) -> Optional[time]:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        for fmt in ('%H:%M', '%H:%M:%S'):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                pass
    return None


def _parse_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                pass
    return None


def parse_attendance_excel(file_path: str) -> list[AttendanceRow]:
    wb = load_workbook(file_path, data_only=True)
    ws = wb.active
    rows = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # skip header
        if not row[0]:
            continue  # skip empty rows
        emp_code = str(row[0]).strip() if row[0] else None
        if not emp_code:
            continue
        parsed_date = _parse_date(row[2])
        if not parsed_date:
            continue
        rows.append(AttendanceRow(
            employee_code=emp_code,
            employee_name=str(row[1]).strip() if row[1] else '',
            date=parsed_date,
            check_in=_parse_time(row[3]),
            check_out=_parse_time(row[4]),
            shift_code=str(row[5]).strip() if row[5] else '',
        ))
    return rows
```

**Step 4: Write attendance/models.py**

```python
from django.db import models
from employees.models import Employee
from accounts.models import User


class AttendanceUpload(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'processing', 'Đang xử lý'
        DONE = 'done', 'Hoàn thành'
        ERROR = 'error', 'Lỗi'

    file = models.FileField(upload_to='attendance_uploads/%Y/%m/')
    month = models.CharField(max_length=7)  # YYYY-MM
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING)
    total_records = models.IntegerField(default=0)
    error_records = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Upload {self.month} - {self.uploaded_at}'

    class Meta:
        verbose_name = 'File chấm công'
        ordering = ['-uploaded_at']


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        OK = 'ok', 'Bình thường'
        ERROR = 'error', 'Lỗi'

    upload = models.ForeignKey(AttendanceUpload, on_delete=models.CASCADE, related_name='records')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    shift_code = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
    error_types = models.JSONField(default=list)

    class Meta:
        verbose_name = 'Bản ghi chấm công'
        unique_together = [['upload', 'employee', 'date']]
        ordering = ['date', 'employee__code']

    def __str__(self):
        return f'{self.employee.code} - {self.date}'
```

**Step 5: Migrate and run tests**

```bash
python manage.py makemigrations attendance
python manage.py migrate
pytest attendance/tests/test_parser.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add attendance/
git commit -m "feat: attendance upload models and Excel parser"
```

---

## Task 7: Error Detection (Config-Driven)

**Files:**
- Create: `attendance/error_detector.py`
- Create: `attendance/tests/test_error_detector.py`
- Modify: `attendance/models.py` — add ErrorType model

**Step 1: Write failing tests**

```python
# attendance/tests/test_error_detector.py
import pytest
from datetime import time
from attendance.error_detector import detect_errors, ErrorCode
from attendance.parser import AttendanceRow
from datetime import date

def make_row(check_in=None, check_out=None, shift_code='HC'):
    return AttendanceRow(
        employee_code='NV001', employee_name='Test',
        date=date(2026, 5, 1),
        check_in=check_in, check_out=check_out, shift_code=shift_code
    )

def test_no_error_normal_day():
    row = make_row(check_in=time(8, 0), check_out=time(17, 0))
    errors = detect_errors(row, rules={})
    assert len(errors) == 0

def test_missing_checkin():
    row = make_row(check_in=None, check_out=time(17, 0))
    errors = detect_errors(row, rules={})
    assert ErrorCode.MISSING_IN in errors

def test_missing_checkout():
    row = make_row(check_in=time(8, 0), check_out=None)
    errors = detect_errors(row, rules={})
    assert ErrorCode.MISSING_OUT in errors

def test_absent():
    row = make_row(check_in=None, check_out=None)
    errors = detect_errors(row, rules={})
    assert ErrorCode.ABSENT in errors
    assert ErrorCode.MISSING_IN not in errors

def test_late_arrival():
    row = make_row(check_in=time(8, 16), check_out=time(17, 0))
    rules = {'late_threshold_minutes': 15, 'standard_start': '08:00'}
    errors = detect_errors(row, rules=rules)
    assert ErrorCode.LATE in errors

def test_early_leave():
    row = make_row(check_in=time(8, 0), check_out=time(16, 44))
    rules = {'early_leave_threshold_minutes': 15, 'standard_end': '17:00'}
    errors = detect_errors(row, rules=rules)
    assert ErrorCode.EARLY_LEAVE in errors
```

**Step 2: Run tests to verify fail**

```bash
pytest attendance/tests/test_error_detector.py -v
```

Expected: FAIL

**Step 3: Write attendance/error_detector.py**

```python
from dataclasses import dataclass
from datetime import time, datetime
from enum import Enum
from typing import Optional
from attendance.parser import AttendanceRow


class ErrorCode(str, Enum):
    MISSING_IN = 'MISSING_IN'
    MISSING_OUT = 'MISSING_OUT'
    ABSENT = 'ABSENT'
    LATE = 'LATE'
    EARLY_LEAVE = 'EARLY_LEAVE'


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _parse_time(s: str) -> time:
    return datetime.strptime(s, '%H:%M').time()


def detect_errors(row: AttendanceRow, rules: dict) -> list[ErrorCode]:
    if row.check_in is None and row.check_out is None:
        return [ErrorCode.ABSENT]

    errors = []

    if row.check_in is None:
        errors.append(ErrorCode.MISSING_IN)

    if row.check_out is None:
        errors.append(ErrorCode.MISSING_OUT)

    if row.check_in and 'standard_start' in rules:
        standard = _parse_time(rules['standard_start'])
        threshold = rules.get('late_threshold_minutes', 15)
        if _to_minutes(row.check_in) > _to_minutes(standard) + threshold:
            errors.append(ErrorCode.LATE)

    if row.check_out and 'standard_end' in rules:
        standard = _parse_time(rules['standard_end'])
        threshold = rules.get('early_leave_threshold_minutes', 15)
        if _to_minutes(row.check_out) < _to_minutes(standard) - threshold:
            errors.append(ErrorCode.EARLY_LEAVE)

    return errors
```

**Step 4: Add ErrorType model to attendance/models.py**

```python
class ErrorType(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    detection_rule = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.code} - {self.name}'

    class Meta:
        verbose_name = 'Loại lỗi chấm công'
```

**Step 5: Add default ErrorType fixtures — management command**

```python
# attendance/management/commands/seed_error_types.py
from django.core.management.base import BaseCommand
from attendance.models import ErrorType

DEFAULTS = [
    {'code': 'MISSING_IN', 'name': 'Thiếu giờ vào', 'description': 'Không có dữ liệu chấm thẻ vào'},
    {'code': 'MISSING_OUT', 'name': 'Thiếu giờ ra', 'description': 'Không có dữ liệu chấm thẻ ra'},
    {'code': 'ABSENT', 'name': 'Vắng mặt', 'description': 'Không có dữ liệu chấm công cả ngày'},
    {'code': 'LATE', 'name': 'Đi muộn', 'description': 'Giờ vào trễ hơn tiêu chuẩn',
     'detection_rule': {'standard_start': '08:00', 'late_threshold_minutes': 15}},
    {'code': 'EARLY_LEAVE', 'name': 'Về sớm', 'description': 'Giờ ra sớm hơn tiêu chuẩn',
     'detection_rule': {'standard_end': '17:00', 'early_leave_threshold_minutes': 15}},
]

class Command(BaseCommand):
    def handle(self, *args, **options):
        for d in DEFAULTS:
            ErrorType.objects.get_or_create(code=d['code'], defaults=d)
        self.stdout.write('Seeded error types.')
```

**Step 6: Migrate and run tests**

```bash
python manage.py makemigrations attendance
python manage.py migrate
python manage.py seed_error_types
pytest attendance/tests/test_error_detector.py -v
```

Expected: All PASS

**Step 7: Commit**

```bash
git add attendance/
git commit -m "feat: config-driven error detection for attendance"
```

---

## Task 8: Explanation Models

**Files:**
- Create: `explanations/models.py`
- Create: `explanations/tests/test_models.py`
- Modify: `explanations/admin.py`

**Step 1: Write failing tests**

```python
# explanations/tests/test_models.py
import pytest
from django.utils import timezone
from explanations.models import ExplanationReason, Explanation
from attendance.models import AttendanceRecord, AttendanceUpload
from employees.models import Employee, Department
from accounts.models import User
from datetime import date

@pytest.fixture
def setup(db):
    user = User.objects.create_user(email='emp@example.com', password='pass')
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)
    tbp_user = User.objects.create_user(email='tbp@example.com', password='pass', role=User.Role.TBP)
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=user)
    record = AttendanceRecord.objects.create(
        upload=upload, employee=emp, date=date(2026, 5, 1),
        status='error', error_types=['MISSING_IN']
    )
    reason = ExplanationReason.objects.create(name='Quên chấm thẻ')
    return {'emp': emp, 'record': record, 'reason': reason, 'tbp_user': tbp_user}

@pytest.mark.django_db
def test_create_explanation(setup):
    s = setup
    exp = Explanation.objects.create(
        record=s['record'], employee=s['emp'],
        reason=s['reason'], note='Tôi quên chấm thẻ'
    )
    assert exp.status == Explanation.Status.PENDING

@pytest.mark.django_db
def test_approve_explanation(setup):
    s = setup
    exp = Explanation.objects.create(record=s['record'], employee=s['emp'], reason=s['reason'])
    exp.status = Explanation.Status.APPROVED
    exp.reviewed_by = s['tbp_user']
    exp.reviewed_at = timezone.now()
    exp.save()
    assert exp.status == Explanation.Status.APPROVED

@pytest.mark.django_db
def test_reject_explanation(setup):
    s = setup
    exp = Explanation.objects.create(record=s['record'], employee=s['emp'], reason=s['reason'])
    exp.status = Explanation.Status.REJECTED
    exp.reviewer_note = 'Không hợp lệ'
    exp.save()
    assert exp.status == Explanation.Status.REJECTED
```

**Step 2: Run tests to verify fail**

```bash
mkdir -p explanations/tests && touch explanations/tests/__init__.py
pytest explanations/tests/test_models.py -v
```

Expected: FAIL

**Step 3: Write explanations/models.py**

```python
from django.db import models
from attendance.models import AttendanceRecord
from employees.models import Employee
from accounts.models import User


class ExplanationReason(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Lý do giải trình'
        ordering = ['order', 'name']


class Explanation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ duyệt'
        APPROVED = 'approved', 'Đã duyệt'
        REJECTED = 'rejected', 'Từ chối'

    record = models.OneToOneField(
        AttendanceRecord, on_delete=models.CASCADE, related_name='explanation'
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='explanations')
    reason = models.ForeignKey(ExplanationReason, on_delete=models.PROTECT)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_explanations'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_note = models.TextField(blank=True)

    def __str__(self):
        return f'{self.employee.code} - {self.record.date} - {self.status}'

    class Meta:
        verbose_name = 'Giải trình'
        ordering = ['-submitted_at']
```

**Step 4: Migrate and run tests**

```bash
python manage.py makemigrations explanations
python manage.py migrate
pytest explanations/tests/test_models.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add explanations/
git commit -m "feat: Explanation and ExplanationReason models"
```

---

## Task 9: Leave Management Models

**Files:**
- Create: `employees/leave_models.py` (appended to employees/models.py)
- Create: `employees/tests/test_leave_models.py`

**Step 1: Write failing tests**

```python
# employees/tests/test_leave_models.py
import pytest
from employees.models import Department, Employee, LeaveBalance, LeaveTransaction
from accounts.models import User

@pytest.fixture
def employee(db):
    user = User.objects.create_user(email='emp@example.com', password='pass')
    dept = Department.objects.create(name='KD')
    return Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)

@pytest.mark.django_db
def test_create_leave_balance(employee):
    lb = LeaveBalance.objects.create(employee=employee, year=2026, total_days=12)
    assert lb.used_days == 0
    assert lb.remaining_days == 12

@pytest.mark.django_db
def test_leave_balance_remaining_computed(employee):
    lb = LeaveBalance.objects.create(employee=employee, year=2026, total_days=12, used_days=3)
    assert lb.remaining_days == 9

@pytest.mark.django_db
def test_leave_transaction(employee):
    lb = LeaveBalance.objects.create(employee=employee, year=2026, total_days=12)
    from datetime import date
    t = LeaveTransaction.objects.create(
        employee=employee, leave_balance=lb,
        date=date(2026, 5, 1), days=1, month='2026-05'
    )
    assert t.days == 1
```

**Step 2: Run tests to verify fail**

```bash
pytest employees/tests/test_leave_models.py -v
```

Expected: FAIL

**Step 3: Add to employees/models.py**

```python
class LeaveBalance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    year = models.IntegerField()
    total_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    @property
    def remaining_days(self):
        return self.total_days - self.used_days

    class Meta:
        unique_together = [['employee', 'year']]
        verbose_name = 'Số ngày phép'

    def __str__(self):
        return f'{self.employee.code} - {self.year}: {self.remaining_days} ngày còn lại'


class LeaveTransaction(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_transactions')
    leave_balance = models.ForeignKey(LeaveBalance, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField()
    days = models.DecimalField(max_digits=4, decimal_places=1)
    month = models.CharField(max_length=7)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Giao dịch phép'
        ordering = ['-date']
```

**Step 4: Migrate and run tests**

```bash
python manage.py makemigrations employees
python manage.py migrate
pytest employees/tests/test_leave_models.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add employees/
git commit -m "feat: LeaveBalance and LeaveTransaction models"
```

---

## Task 10: Employee-Facing Views (Attendance + Explanation)

**Files:**
- Create: `attendance/views.py`
- Create: `attendance/urls.py`
- Create: `explanations/views.py`
- Create: `explanations/urls.py`
- Create: `templates/attendance/my_attendance.html`
- Create: `templates/explanations/submit.html`
- Create: `templates/explanations/my_explanations.html`
- Create: `attendance/tests/test_views.py`

**Step 1: Write failing tests**

```python
# attendance/tests/test_views.py
import pytest
from django.test import Client
from django.urls import reverse
from accounts.models import User
from employees.models import Employee, Department
from attendance.models import AttendanceUpload, AttendanceRecord
from datetime import date

@pytest.fixture
def emp_user(db):
    user = User.objects.create_user(email='emp@example.com', password='pass', role=User.Role.EMPLOYEE)
    dept = Department.objects.create(name='KD')
    Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)
    return user

def test_my_attendance_requires_login():
    client = Client()
    response = client.get('/attendance/')
    assert response.status_code == 302
    assert '/accounts/login/' in response['Location']

@pytest.mark.django_db
def test_my_attendance_loads(emp_user):
    client = Client()
    client.force_login(emp_user)
    response = client.get('/attendance/')
    assert response.status_code == 200

@pytest.mark.django_db
def test_my_attendance_shows_records(emp_user):
    client = Client()
    client.force_login(emp_user)
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=emp_user)
    AttendanceRecord.objects.create(
        upload=upload, employee=emp_user.employee_profile,
        date=date(2026, 5, 1), status='ok'
    )
    response = client.get('/attendance/?month=2026-05')
    assert response.status_code == 200
    assert b'NV001' in response.content or b'2026-05-01' in response.content
```

**Step 2: Run tests to verify fail**

```bash
pytest attendance/tests/test_views.py -v
```

Expected: FAIL

**Step 3: Write attendance/views.py (employee view)**

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from .models import AttendanceRecord, AttendanceUpload
from datetime import date


@login_required
def my_attendance(request):
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
```

**Step 4: Write attendance/urls.py**

```python
from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.my_attendance, name='my_attendance'),
    path('upload/', views.upload_attendance, name='upload'),
    path('upload/<int:pk>/', views.upload_detail, name='upload_detail'),
]
```

**Step 5: Create templates/attendance/my_attendance.html**

```html
{% extends "base/base.html" %}
{% block title %}Chấm công của tôi{% endblock %}
{% block content %}
<div class="row">
    <div class="col-12">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h4><i class="bi bi-calendar-check"></i> Chấm công — {{ employee.full_name }}</h4>
            <select class="form-select w-auto" onchange="window.location='?month='+this.value">
                {% for m in months %}
                <option value="{{ m }}" {% if m == month %}selected{% endif %}>{{ m }}</option>
                {% endfor %}
            </select>
        </div>

        <!-- Desktop table -->
        <div class="d-none d-md-block">
            <table class="table table-bordered table-hover">
                <thead class="table-light">
                    <tr>
                        <th>Ngày</th><th>Giờ vào</th><th>Giờ ra</th>
                        <th>Ca</th><th>Trạng thái</th><th>Giải trình</th>
                    </tr>
                </thead>
                <tbody>
                    {% for rec in records %}
                    <tr>
                        <td>{{ rec.date }}</td>
                        <td>{{ rec.check_in|default:"-" }}</td>
                        <td>{{ rec.check_out|default:"-" }}</td>
                        <td>{{ rec.shift_code }}</td>
                        <td>
                            {% if rec.status == 'ok' %}
                                <span class="badge bg-success">Bình thường</span>
                            {% elif rec.status == 'error' %}
                                {% if rec.explanation %}
                                    {% if rec.explanation.status == 'pending' %}
                                        <span class="badge bg-warning text-dark">Chờ duyệt</span>
                                    {% elif rec.explanation.status == 'approved' %}
                                        <span class="badge bg-info">Đã duyệt</span>
                                    {% else %}
                                        <span class="badge bg-secondary">Từ chối</span>
                                    {% endif %}
                                {% else %}
                                    <span class="badge bg-danger">Lỗi</span>
                                {% endif %}
                            {% endif %}
                        </td>
                        <td>
                            {% if rec.status == 'error' and not rec.explanation %}
                            <a href="/explanations/submit/{{ rec.pk }}/" class="btn btn-sm btn-outline-primary">Giải trình</a>
                            {% elif rec.explanation and rec.explanation.status == 'pending' %}
                            <a href="/explanations/submit/{{ rec.pk }}/" class="btn btn-sm btn-outline-secondary">Sửa</a>
                            {% endif %}
                        </td>
                    </tr>
                    {% empty %}
                    <tr><td colspan="6" class="text-center text-muted">Chưa có dữ liệu chấm công tháng này</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Mobile cards -->
        <div class="d-md-none">
            {% for rec in records %}
            <div class="card mb-2">
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between">
                        <strong>{{ rec.date }}</strong>
                        {% if rec.status == 'ok' %}
                            <span class="badge bg-success">OK</span>
                        {% elif rec.status == 'error' %}
                            {% if rec.explanation %}
                                <span class="badge bg-warning text-dark">Chờ duyệt</span>
                            {% else %}
                                <span class="badge bg-danger">Lỗi</span>
                            {% endif %}
                        {% endif %}
                    </div>
                    <small class="text-muted">Vào: {{ rec.check_in|default:"-" }} | Ra: {{ rec.check_out|default:"-" }} | Ca: {{ rec.shift_code }}</small>
                    {% if rec.status == 'error' and not rec.explanation %}
                    <div class="mt-1">
                        <a href="/explanations/submit/{{ rec.pk }}/" class="btn btn-sm btn-outline-primary w-100">Giải trình</a>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% empty %}
            <p class="text-muted text-center">Chưa có dữ liệu</p>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
```

**Step 6: Write explanations/views.py**

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Explanation, ExplanationReason
from attendance.models import AttendanceRecord
from accounts.models import User


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

    dept = None
    if request.user.is_tbp and not request.user.is_hr:
        try:
            dept = request.user.managed_departments.first()
        except Exception:
            pass

    qs = Explanation.objects.filter(status=Explanation.Status.PENDING).select_related(
        'employee__department', 'record', 'reason'
    )
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
```

**Step 7: Write explanations/urls.py**

```python
from django.urls import path
from . import views

app_name = 'explanations'

urlpatterns = [
    path('submit/<int:record_id>/', views.submit_explanation, name='submit'),
    path('my/', views.my_explanations, name='my_explanations'),
    path('pending/', views.pending_approvals, name='pending_approvals'),
    path('review/<int:pk>/', views.review_explanation, name='review'),
]
```

**Step 8: Update hrms/urls.py**

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('attendance/', include('attendance.urls')),
    path('explanations/', include('explanations.urls')),
    path('employees/', include('employees.urls')),
    path('reports/', include('reports.urls')),
    path('', lambda request: redirect('attendance:my_attendance'), name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Step 9: Run tests**

```bash
pytest attendance/tests/test_views.py -v
```

Expected: All PASS

**Step 10: Commit**

```bash
git add attendance/ explanations/ hrms/ templates/
git commit -m "feat: employee attendance view and explanation submission"
```

---

## Task 11: HR Upload View & Processing Pipeline

**Files:**
- Create: `attendance/upload_processor.py`
- Create: `attendance/tests/test_upload_processor.py`
- Modify: `attendance/views.py` — add HR upload views
- Create: `templates/attendance/upload.html`
- Create: `templates/attendance/upload_detail.html`

**Step 1: Write failing tests**

```python
# attendance/tests/test_upload_processor.py
import pytest
from datetime import time, date
from attendance.upload_processor import process_upload
from attendance.models import AttendanceUpload, AttendanceRecord
from attendance.parser import AttendanceRow
from employees.models import Employee, Department
from accounts.models import User

@pytest.fixture
def setup(db):
    hr_user = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(
        user=User.objects.create_user(email='emp@example.com', password='pass'),
        code='NV001', full_name='A', department=dept
    )
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr_user)
    return {'upload': upload, 'emp': emp}

@pytest.mark.django_db
def test_process_normal_row(setup):
    rows = [AttendanceRow('NV001', 'A', date(2026, 5, 1), time(8, 0), time(17, 0), 'HC')]
    process_upload(setup['upload'], rows)
    records = AttendanceRecord.objects.filter(upload=setup['upload'])
    assert records.count() == 1
    assert records.first().status == 'ok'

@pytest.mark.django_db
def test_process_missing_checkin_creates_error(setup):
    rows = [AttendanceRow('NV001', 'A', date(2026, 5, 1), None, time(17, 0), 'HC')]
    process_upload(setup['upload'], rows)
    record = AttendanceRecord.objects.get(upload=setup['upload'])
    assert record.status == 'error'
    assert 'MISSING_IN' in record.error_types

@pytest.mark.django_db
def test_process_unknown_employee_skips(setup):
    rows = [AttendanceRow('NV999', 'Unknown', date(2026, 5, 1), time(8, 0), time(17, 0), 'HC')]
    process_upload(setup['upload'], rows)
    assert AttendanceRecord.objects.filter(upload=setup['upload']).count() == 0
```

**Step 2: Run tests to verify fail**

```bash
pytest attendance/tests/test_upload_processor.py -v
```

Expected: FAIL

**Step 3: Write attendance/upload_processor.py**

```python
from attendance.models import AttendanceUpload, AttendanceRecord, ErrorType
from attendance.parser import AttendanceRow
from attendance.error_detector import detect_errors
from employees.models import Employee


def _build_rules() -> dict:
    rules = {}
    for et in ErrorType.objects.filter(is_active=True):
        if et.detection_rule:
            rules.update(et.detection_rule)
    return rules


def process_upload(upload: AttendanceUpload, rows: list[AttendanceRow]):
    employee_map = {emp.code: emp for emp in Employee.objects.filter(is_active=True)}
    rules = _build_rules()
    total = 0
    errors = 0

    for row in rows:
        emp = employee_map.get(row.employee_code)
        if not emp:
            continue

        error_codes = detect_errors(row, rules)
        status = 'error' if error_codes else 'ok'

        AttendanceRecord.objects.update_or_create(
            upload=upload,
            employee=emp,
            date=row.date,
            defaults={
                'check_in': row.check_in,
                'check_out': row.check_out,
                'shift_code': row.shift_code,
                'status': status,
                'error_types': [e.value for e in error_codes],
            }
        )
        total += 1
        if status == 'error':
            errors += 1

    upload.total_records = total
    upload.error_records = errors
    upload.status = AttendanceUpload.Status.DONE
    upload.save()
```

**Step 4: Add HR upload views to attendance/views.py**

```python
from django.contrib.auth.decorators import login_required
from .upload_processor import process_upload
from .parser import parse_attendance_excel
from .forms import AttendanceUploadForm
import os


@login_required
def upload_attendance(request):
    if not request.user.is_hr:
        return redirect('attendance:my_attendance')

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
    records_with_errors = upload.records.filter(status='error').select_related('employee')
    return render(request, 'attendance/upload_detail.html', {
        'upload': upload, 'error_records': records_with_errors
    })
```

**Step 5: Create attendance/forms.py**

```python
from django import forms
from .models import AttendanceUpload


class AttendanceUploadForm(forms.ModelForm):
    class Meta:
        model = AttendanceUpload
        fields = ['file', 'month']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx'}),
            'month': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM'}),
        }
```

**Step 6: Run tests**

```bash
pytest attendance/tests/test_upload_processor.py -v
```

Expected: All PASS

**Step 7: Commit**

```bash
git add attendance/
git commit -m "feat: HR attendance upload view and processing pipeline"
```

---

## Task 12: Attendance Calculation & Leave Deduction

**Files:**
- Create: `reports/models.py`
- Create: `reports/calculator.py`
- Create: `reports/tests/test_calculator.py`

**Step 1: Write failing tests**

```python
# reports/tests/test_calculator.py
import pytest
from datetime import date
from reports.calculator import calculate_month
from attendance.models import AttendanceUpload, AttendanceRecord
from explanations.models import Explanation, ExplanationReason
from employees.models import Employee, Department, LeaveBalance
from accounts.models import User

@pytest.fixture
def setup(db):
    user = User.objects.create_user(email='emp@example.com', password='pass')
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)
    hr = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr, status='done')
    lb = LeaveBalance.objects.create(employee=emp, year=2026, total_days=12)
    return {'emp': emp, 'upload': upload, 'lb': lb, 'hr': hr}

@pytest.mark.django_db
def test_calculate_all_ok_days(setup):
    s = setup
    for d in range(1, 6):
        AttendanceRecord.objects.create(
            upload=s['upload'], employee=s['emp'],
            date=date(2026, 5, d), status='ok'
        )
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert calc.actual_workdays == 5
    assert calc.leave_days_used == 0

@pytest.mark.django_db
def test_approved_explanation_counts_as_workday(setup):
    s = setup
    record = AttendanceRecord.objects.create(
        upload=s['upload'], employee=s['emp'],
        date=date(2026, 5, 1), status='error', error_types=['MISSING_IN']
    )
    reason = ExplanationReason.objects.create(name='Quên chấm')
    Explanation.objects.create(
        record=record, employee=s['emp'], reason=reason,
        status=Explanation.Status.APPROVED
    )
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert calc.actual_workdays == 1
    assert calc.leave_days_used == 0
```

**Step 2: Run tests to verify fail**

```bash
mkdir -p reports/tests && touch reports/tests/__init__.py
pytest reports/tests/test_calculator.py -v
```

Expected: FAIL

**Step 3: Write reports/models.py**

```python
from django.db import models
from employees.models import Employee
from accounts.models import User


class AttendanceCalculation(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Nháp'
        FINALIZED = 'finalized', 'Đã chốt'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='calculations')
    month = models.CharField(max_length=7)
    actual_workdays = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    leave_days_used = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    calculated_at = models.DateTimeField(auto_now=True)
    calculated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [['employee', 'month']]
        verbose_name = 'Kết quả tính công'
        ordering = ['employee__code']

    def __str__(self):
        return f'{self.employee.code} - {self.month}'
```

**Step 4: Write reports/calculator.py**

```python
from decimal import Decimal
from attendance.models import AttendanceRecord
from explanations.models import Explanation
from employees.models import Employee, LeaveBalance
from reports.models import AttendanceCalculation
from accounts.models import User


def calculate_month(month: str, calculated_by: User) -> dict:
    records = AttendanceRecord.objects.filter(
        upload__month=month
    ).select_related('employee', 'explanation')

    results = {}

    for record in records:
        code = record.employee.code
        if code not in results:
            results[code] = {'employee': record.employee, 'workdays': Decimal(0), 'leave': Decimal(0)}

        if record.status == 'ok':
            results[code]['workdays'] += Decimal(1)
        elif record.status == 'error':
            exp = getattr(record, 'explanation', None)
            if exp and exp.status == Explanation.Status.APPROVED:
                results[code]['workdays'] += Decimal(1)
            else:
                results[code]['leave'] += Decimal(1)

    calcs = {}
    for code, data in results.items():
        emp = data['employee']
        calc, _ = AttendanceCalculation.objects.update_or_create(
            employee=emp,
            month=month,
            defaults={
                'actual_workdays': data['workdays'],
                'leave_days_used': data['leave'],
                'calculated_by': calculated_by,
                'status': AttendanceCalculation.Status.DRAFT,
            }
        )
        calcs[code] = calc

    return calcs
```

**Step 5: Migrate and run tests**

```bash
python manage.py makemigrations reports
python manage.py migrate
pytest reports/tests/test_calculator.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add reports/
git commit -m "feat: attendance calculation engine with leave deduction"
```

---

## Task 13: Excel Export

**Files:**
- Create: `reports/exporter.py`
- Create: `reports/tests/test_exporter.py`
- Create: `reports/views.py`
- Create: `reports/urls.py`
- Create: `templates/reports/calculate.html`

**Step 1: Write failing tests**

```python
# reports/tests/test_exporter.py
import pytest
from reports.exporter import export_calculation_excel
from reports.models import AttendanceCalculation
from employees.models import Employee, Department, LeaveBalance
from accounts.models import User
import tempfile, os
from openpyxl import load_workbook

@pytest.fixture
def setup(db):
    user = User.objects.create_user(email='emp@example.com', password='pass')
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(user=user, code='NV001', full_name='Nguyen Van A', department=dept)
    hr = User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)
    LeaveBalance.objects.create(employee=emp, year=2026, total_days=12, used_days=2)
    AttendanceCalculation.objects.create(
        employee=emp, month='2026-05', actual_workdays=20, leave_days_used=2, calculated_by=hr
    )
    return {'emp': emp}

@pytest.mark.django_db
def test_export_creates_file(setup):
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    tmp.close()
    export_calculation_excel('2026-05', tmp.name)
    wb = load_workbook(tmp.name)
    os.unlink(tmp.name)
    assert wb is not None
    ws = wb.active
    assert ws.max_row >= 2

@pytest.mark.django_db
def test_export_contains_employee_data(setup):
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    tmp.close()
    export_calculation_excel('2026-05', tmp.name)
    wb = load_workbook(tmp.name)
    os.unlink(tmp.name)
    ws = wb.active
    data = [[cell.value for cell in row] for row in ws.iter_rows()]
    flat = [str(v) for row in data for v in row if v is not None]
    assert 'NV001' in flat
    assert 'Nguyen Van A' in flat
```

**Step 2: Run tests to verify fail**

```bash
pytest reports/tests/test_exporter.py -v
```

Expected: FAIL

**Step 3: Write reports/exporter.py**

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reports.models import AttendanceCalculation
from employees.models import LeaveBalance


def export_calculation_excel(month: str, output_path: str):
    calcs = AttendanceCalculation.objects.filter(month=month).select_related(
        'employee__department'
    ).order_by('employee__department__name', 'employee__code')

    wb = Workbook()
    ws = wb.active
    ws.title = f'Tổng hợp công {month}'

    header_font = Font(bold=True)
    title_fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
    title_font = Font(bold=True, color='FFFFFF', size=12)
    header_fill = PatternFill(start_color='D6E4F0', end_color='D6E4F0', fill_type='solid')
    thin = Side(style='thin')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal='center')

    # Row 1: Title
    ws.merge_cells('A1:H1')
    ws['A1'] = f'BẢNG TỔNG HỢP CÔNG THÁNG {month}'
    ws['A1'].font = title_font
    ws['A1'].fill = title_fill
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30

    # Row 2: Empty
    ws.append([])

    # Row 3: Headers
    headers = ['STT', 'Mã NV', 'Họ tên', 'Phòng ban', 'Ngày công', 'Ngày phép dùng', 'Phép còn lại', 'Ghi chú']
    ws.append(headers)
    for col, _ in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = center

    # Data rows
    for i, calc in enumerate(calcs, 1):
        emp = calc.employee
        try:
            lb = LeaveBalance.objects.get(employee=emp, year=int(month[:4]))
            remaining = lb.remaining_days
        except LeaveBalance.DoesNotExist:
            remaining = '-'

        row = [i, emp.code, emp.full_name, emp.department.name,
               float(calc.actual_workdays), float(calc.leave_days_used), remaining, '']
        ws.append(row)
        row_idx = ws.max_row
        for col in range(1, 9):
            ws.cell(row=row_idx, column=col).border = border
            if col in (1, 5, 6, 7):
                ws.cell(row=row_idx, column=col).alignment = center

    # Column widths
    widths = [6, 10, 25, 20, 12, 18, 14, 20]
    for col, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    wb.save(output_path)
```

**Step 4: Write reports/views.py**

```python
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.contrib import messages
from reports.calculator import calculate_month
from reports.exporter import export_calculation_excel
from attendance.models import AttendanceUpload
import tempfile
import os


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
```

**Step 5: Write reports/urls.py**

```python
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('calculate/', views.calculate_view, name='calculate'),
]
```

**Step 6: Run tests**

```bash
pytest reports/tests/test_exporter.py -v
```

Expected: All PASS

**Step 7: Commit**

```bash
git add reports/
git commit -m "feat: Excel export for attendance calculation results"
```

---

## Task 14: HR Employee Management Views

**Files:**
- Create: `employees/views.py`
- Create: `employees/urls.py`
- Create: `templates/employees/list.html`
- Create: `templates/employees/form.html`
- Create: `templates/employees/leave_balance.html`

**Step 1: Write failing tests**

```python
# employees/tests/test_views.py
import pytest
from django.test import Client
from accounts.models import User

@pytest.fixture
def hr_user(db):
    return User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)

def test_employee_list_requires_hr():
    client = Client()
    response = client.get('/employees/')
    assert response.status_code == 302

@pytest.mark.django_db
def test_employee_list_loads_for_hr(hr_user):
    client = Client()
    client.force_login(hr_user)
    response = client.get('/employees/')
    assert response.status_code == 200
```

**Step 2: Run tests to verify fail**

```bash
mkdir -p employees/tests && touch employees/tests/__init__.py
pytest employees/tests/test_views.py -v
```

Expected: FAIL

**Step 3: Write employees/views.py**

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Employee, Department, LeaveBalance
from .forms import EmployeeForm, LeaveBalanceForm
from accounts.models import User


def _hr_required(request):
    return request.user.is_authenticated and request.user.is_hr


@login_required
def employee_list(request):
    if not _hr_required(request):
        return redirect('attendance:my_attendance')
    employees = Employee.objects.select_related('department', 'user').order_by('code')
    return render(request, 'employees/list.html', {'employees': employees})


@login_required
def employee_create(request):
    if not _hr_required(request):
        return redirect('attendance:my_attendance')
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm nhân viên.')
            return redirect('employees:list')
    else:
        form = EmployeeForm()
    return render(request, 'employees/form.html', {'form': form, 'action': 'Thêm mới'})


@login_required
def employee_edit(request, pk):
    if not _hr_required(request):
        return redirect('attendance:my_attendance')
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=emp)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật nhân viên.')
            return redirect('employees:list')
    else:
        form = EmployeeForm(instance=emp)
    return render(request, 'employees/form.html', {'form': form, 'action': 'Cập nhật', 'emp': emp})


@login_required
def leave_balance_view(request, pk):
    if not _hr_required(request):
        return redirect('attendance:my_attendance')
    emp = get_object_or_404(Employee, pk=pk)
    balances = LeaveBalance.objects.filter(employee=emp).order_by('-year')
    if request.method == 'POST':
        form = LeaveBalanceForm(request.POST)
        if form.is_valid():
            lb = form.save(commit=False)
            lb.employee = emp
            lb.save()
            messages.success(request, 'Đã cập nhật số ngày phép.')
            return redirect('employees:leave_balance', pk=pk)
    else:
        form = LeaveBalanceForm(initial={'employee': emp})
    return render(request, 'employees/leave_balance.html', {
        'emp': emp, 'balances': balances, 'form': form
    })
```

**Step 4: Write employees/forms.py**

```python
from django import forms
from .models import Employee, LeaveBalance, Department
from accounts.models import User


class EmployeeForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Để trống nếu không đổi mật khẩu'
    )

    class Meta:
        model = Employee
        fields = ['code', 'full_name', 'department', 'position', 'start_date', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def save(self, commit=True):
        emp = super().save(commit=False)
        email = self.cleaned_data['email']
        password = self.cleaned_data.get('password')
        if emp.pk:
            user = emp.user
            user.email = email
            user.username = email
            if password:
                user.set_password(password)
            user.save()
        else:
            user = User.objects.create_user(email=email, password=password or User.objects.make_random_password())
            emp.user = user
        if commit:
            emp.save()
        return emp


class LeaveBalanceForm(forms.ModelForm):
    class Meta:
        model = LeaveBalance
        fields = ['year', 'total_days', 'used_days']
        widgets = {
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_days': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'used_days': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        }
```

**Step 5: Write employees/urls.py**

```python
from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    path('', views.employee_list, name='list'),
    path('create/', views.employee_create, name='create'),
    path('<int:pk>/edit/', views.employee_edit, name='edit'),
    path('<int:pk>/leave/', views.leave_balance_view, name='leave_balance'),
]
```

**Step 6: Run tests**

```bash
pytest employees/tests/test_views.py -v
```

Expected: All PASS

**Step 7: Commit**

```bash
git add employees/
git commit -m "feat: HR employee management views"
```

---

## Task 15: HR Configuration Views

**Files:**
- Create: `accounts/config_views.py`
- Create: `templates/accounts/config.html`
- Modify: `accounts/urls.py`

**Step 1: Write failing tests**

```python
# accounts/tests/test_config_views.py
import pytest
from django.test import Client
from accounts.models import User

@pytest.fixture
def hr_user(db):
    return User.objects.create_user(email='hr@example.com', password='pass', role=User.Role.HR)

@pytest.mark.django_db
def test_config_page_loads(hr_user):
    client = Client()
    client.force_login(hr_user)
    response = client.get('/accounts/config/')
    assert response.status_code == 200

@pytest.mark.django_db
def test_toggle_otp_on(hr_user):
    client = Client()
    client.force_login(hr_user)
    response = client.post('/accounts/config/', {'otp_enabled': 'on'})
    assert response.status_code == 302
    from accounts.otp import is_otp_enabled
    assert is_otp_enabled() is True
```

**Step 2: Run tests to verify fail**

```bash
pytest accounts/tests/test_config_views.py -v
```

Expected: FAIL

**Step 3: Write accounts/config_views.py**

```python
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .otp import is_otp_enabled, set_otp_enabled
from attendance.models import ErrorType
from explanations.models import ExplanationReason


@login_required
def config_view(request):
    if not request.user.is_hr:
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
```

**Step 4: Add to accounts/urls.py**

```python
path('config/', config_views.config_view, name='config'),
```

**Step 5: Run tests**

```bash
pytest accounts/tests/test_config_views.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add accounts/
git commit -m "feat: HR configuration view with OTP toggle"
```

---

## Task 16: Run Full Test Suite & Deployment Config

**Step 1: Run all tests**

```bash
pytest -v
```

Expected: All tests PASS

**Step 2: Create gunicorn config**

```python
# gunicorn.conf.py
bind = '0.0.0.0:8000'
workers = 3
worker_class = 'sync'
timeout = 120
accesslog = '-'
errorlog = '-'
```

**Step 3: Create Makefile for common commands**

```makefile
.PHONY: dev test migrate seed

dev:
	DJANGO_SETTINGS_MODULE=hrms.settings.development python manage.py runserver

test:
	pytest -v

migrate:
	python manage.py migrate

seed:
	python manage.py seed_error_types

createsuperuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput

prod:
	DJANGO_SETTINGS_MODULE=hrms.settings.production gunicorn hrms.wsgi:application -c gunicorn.conf.py
```

**Step 4: Update CLAUDE.md**

```markdown
# HR Attendance System

Django full-stack web app for HR attendance management.

## Quick Start
```bash
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_error_types
python manage.py createsuperuser
make dev
```

## Test
```bash
make test
```

## Roles
- HR: full access
- TBP: approve/reject explanations for their department
- Employee: view own attendance, submit explanations
```

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: deployment config and project documentation"
```

---

## Summary

| Task | Component | Tests |
|---|---|---|
| 1 | Project setup | - |
| 2 | User model + roles | accounts/tests/test_user_model.py |
| 3 | Employee + Department | employees/tests/test_models.py |
| 4 | OTP system | accounts/tests/test_otp.py |
| 5 | Login flow | accounts/tests/test_views.py |
| 6 | Attendance parser | attendance/tests/test_parser.py |
| 7 | Error detection | attendance/tests/test_error_detector.py |
| 8 | Explanation models | explanations/tests/test_models.py |
| 9 | Leave management | employees/tests/test_leave_models.py |
| 10 | Employee views | attendance/tests/test_views.py |
| 11 | HR upload pipeline | attendance/tests/test_upload_processor.py |
| 12 | Calculation engine | reports/tests/test_calculator.py |
| 13 | Excel export | reports/tests/test_exporter.py |
| 14 | HR employee mgmt | employees/tests/test_views.py |
| 15 | Config views | accounts/tests/test_config_views.py |
| 16 | Full test + deploy | - |

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
        extra_fields.setdefault('role', 'HR')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        HR = 'HR', 'HR'
        EMPLOYEE = 'EMPLOYEE', 'Nhân viên'
        TBP = 'TBP', 'Trưởng bộ phận'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    extra_roles = models.JSONField(default=list, blank=True)
    totp_secret = models.CharField(max_length=64, blank=True)
    otp_method = models.CharField(
        max_length=10,
        choices=[('email', 'Email OTP'), ('totp', 'Google Authenticator')],
        default='email'
    )

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
        cls.objects.update_or_create(key=key, defaults={'value': value})

    class Meta:
        verbose_name = 'Cấu hình hệ thống'

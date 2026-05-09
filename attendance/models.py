from django.db import models
from accounts.models import User


class Shift(models.Model):
    code = models.CharField(max_length=100, unique=True, verbose_name='Ký hiệu ca')
    check_in = models.TimeField(null=True, blank=True, verbose_name='Giờ vào')
    check_out = models.TimeField(null=True, blank=True, verbose_name='Giờ ra')
    total_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0, verbose_name='Tổng giờ')
    workday_value = models.DecimalField(max_digits=3, decimal_places=1, default=0, verbose_name='Ngày công')
    leave_day_value = models.DecimalField(max_digits=3, decimal_places=1, default=0, verbose_name='Ngày phép')
    work_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0, verbose_name='Giờ công')
    leave_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0, verbose_name='Giờ phép')
    break_start = models.TimeField(null=True, blank=True, verbose_name='Bắt đầu nghỉ trưa')
    break_end = models.TimeField(null=True, blank=True, verbose_name='Kết thúc nghỉ trưa')
    note = models.TextField(blank=True, verbose_name='Ghi chú')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = 'Ca làm việc'
        verbose_name_plural = 'Ca làm việc'
        ordering = ['code']


class AttendanceUpload(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'processing', 'Đang xử lý'
        DONE = 'done', 'Hoàn thành'
        ERROR = 'error', 'Lỗi'

    file = models.FileField(upload_to='attendance_uploads/%Y/%m/', blank=True)
    month = models.CharField(max_length=7)
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
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    shift_code = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
    error_types = models.JSONField(default=list)
    minutes_late = models.IntegerField(null=True, blank=True)   # phút đi muộn (dương)
    minutes_early = models.IntegerField(null=True, blank=True)  # phút về sớm (dương)

    CI_ERRORS = {'MISSING_IN', 'LATE', 'ABSENT'}
    CO_ERRORS = {'MISSING_OUT', 'EARLY_LEAVE', 'ABSENT'}

    @property
    def has_ci_issue(self):
        return bool(set(self.error_types) & self.CI_ERRORS)

    @property
    def has_co_issue(self):
        return bool(set(self.error_types) & self.CO_ERRORS)

    class Meta:
        verbose_name = 'Bản ghi chấm công'
        unique_together = [['upload', 'employee', 'date']]
        ordering = ['date', 'employee__code']

    def __str__(self):
        return f'{self.employee.code} - {self.date}'


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

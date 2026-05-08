from django.db import models
from accounts.models import User


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
    shift_code = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
    error_types = models.JSONField(default=list)

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

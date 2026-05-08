from django.db import models
from attendance.models import AttendanceRecord
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
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='explanations')
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

from django.db import models
from accounts.models import User


class AttendanceCalculation(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Nháp'
        FINALIZED = 'finalized', 'Đã chốt'

    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='calculations')
    month = models.CharField(max_length=7)
    work_hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    leave_hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    # Legacy day-unit fields (kept for compat; = hours / 8)
    actual_workdays = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    leave_days_used = models.DecimalField(max_digits=5, decimal_places=2, default=0)
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

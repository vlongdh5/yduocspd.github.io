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

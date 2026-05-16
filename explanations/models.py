from django.db import models
from attendance.models import AttendanceRecord
from accounts.models import User

CI_ERRORS = {'MISSING_IN', 'LATE', 'ABSENT'}
CO_ERRORS = {'MISSING_OUT', 'EARLY_LEAVE', 'ABSENT'}


class ExplanationReason(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    # "Nghỉ phép nửa ngày" chỉ áp dụng khi ca làm việc cả ngày (workday_value=1)
    requires_full_day_shift = models.BooleanField(default=False)
    is_compensatory = models.BooleanField(default=False)

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
    employee = models.ForeignKey(
        'employees.Employee', on_delete=models.CASCADE, related_name='explanations'
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    # --- Phía Check-in ---
    ci_reason = models.ForeignKey(
        ExplanationReason, on_delete=models.PROTECT,
        null=True, blank=True, related_name='ci_explanations'
    )
    ci_note = models.TextField(blank=True)
    ci_status = models.CharField(
        max_length=20, choices=Status.choices, null=True, blank=True
    )
    ci_reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ci_reviewed_explanations'
    )
    ci_reviewed_at = models.DateTimeField(null=True, blank=True)
    ci_reviewer_note = models.TextField(blank=True)

    # --- Phía Check-out ---
    co_reason = models.ForeignKey(
        ExplanationReason, on_delete=models.PROTECT,
        null=True, blank=True, related_name='co_explanations'
    )
    co_note = models.TextField(blank=True)
    co_status = models.CharField(
        max_length=20, choices=Status.choices, null=True, blank=True
    )
    co_reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='co_reviewed_explanations'
    )
    co_reviewed_at = models.DateTimeField(null=True, blank=True)
    co_reviewer_note = models.TextField(blank=True)

    # --- Computed properties ---

    @property
    def has_ci_issue(self):
        return bool(set(self.record.error_types) & CI_ERRORS)

    @property
    def has_co_issue(self):
        return bool(set(self.record.error_types) & CO_ERRORS)

    @property
    def ci_submitted(self):
        return self.ci_reason_id is not None

    @property
    def co_submitted(self):
        return self.co_reason_id is not None

    @property
    def is_fully_submitted(self):
        if self.has_ci_issue and not self.ci_submitted:
            return False
        if self.has_co_issue and not self.co_submitted:
            return False
        return True

    @property
    def is_fully_reviewed(self):
        if self.has_ci_issue and self.ci_status == self.Status.PENDING:
            return False
        if self.has_co_issue and self.co_status == self.Status.PENDING:
            return False
        return True

    @property
    def overall_status(self):
        statuses = []
        if self.has_ci_issue and self.ci_status:
            statuses.append(self.ci_status)
        if self.has_co_issue and self.co_status:
            statuses.append(self.co_status)
        if not statuses:
            return self.Status.PENDING
        if all(s == self.Status.APPROVED for s in statuses):
            return self.Status.APPROVED
        if any(s == self.Status.PENDING for s in statuses):
            return self.Status.PENDING
        return self.Status.REJECTED

    def __str__(self):
        return f'{self.employee.code} - {self.record.date} - {self.overall_status}'

    class Meta:
        verbose_name = 'Giải trình'
        ordering = ['-submitted_at']

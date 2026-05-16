# Compensatory Leave Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Thêm quản lý nghỉ bù vào hệ thống — HR cấp giờ bù thủ công, NV chọn dùng giờ bù thay phép khi giải trình, có màn hình theo dõi phép + bù đầy đủ.

**Architecture:** Thêm `CompensatoryBalance` + `CompensatoryTransaction` vào `employees`; thêm `ci_use_compensatory`/`co_use_compensatory` vào `Explanation`; thêm `is_compensatory` vào `ExplanationReason`; cập nhật calculator để trả về 3-tuple và tạo giao dịch bù khi tính lương.

**Tech Stack:** Django 5, pytest-django, openpyxl, Bootstrap 5

---

## Task 1: Thêm `is_compensatory` vào ExplanationReason + seed 2 lý do mới

**Files:**
- Modify: `explanations/models.py`
- Modify: `explanations/management/commands/seed_explanation_reasons.py`
- Test: `explanations/tests/test_models.py`

**Step 1: Viết test kiểm tra field mới**

```python
# explanations/tests/test_models.py — thêm vào cuối file

@pytest.mark.django_db
def test_explanation_reason_is_compensatory_default_false():
    reason = ExplanationReason.objects.create(name='Test')
    assert reason.is_compensatory is False

@pytest.mark.django_db
def test_compensatory_reasons_seeded():
    from django.core.management import call_command
    call_command('seed_explanation_reasons')
    assert ExplanationReason.objects.filter(name='Nghỉ bù cả ngày', is_compensatory=True).exists()
    assert ExplanationReason.objects.filter(name='Nghỉ bù nửa ngày', is_compensatory=True).exists()
```

**Step 2: Chạy test để xác nhận fail**

```bash
pytest explanations/tests/test_models.py::test_explanation_reason_is_compensatory_default_false explanations/tests/test_models.py::test_compensatory_reasons_seeded -v
```
Expected: FAIL với `AttributeError: type object 'ExplanationReason' has no attribute 'is_compensatory'`

**Step 3: Thêm field vào model**

Trong `explanations/models.py`, thêm vào class `ExplanationReason` sau field `requires_full_day_shift`:
```python
    is_compensatory = models.BooleanField(default=False)
```

**Step 4: Cập nhật seed command**

Trong `explanations/management/commands/seed_explanation_reasons.py`, thêm 2 entry vào `DEFAULTS` và cập nhật `get_or_create` để xử lý `is_compensatory`:

```python
DEFAULTS = [
    {'name': 'Đi muộn/ Về sớm', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Quên chấm công', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Trị liệu tại nhà', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Đi công tác/ tổ chức sự kiện/ công việc khác theo chỉ đạo', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Nghỉ phép cả ngày', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Nghỉ không lương', 'requires_full_day_shift': False, 'is_compensatory': False},
    {'name': 'Nghỉ phép nửa ngày', 'requires_full_day_shift': True, 'is_compensatory': False},
    {'name': 'Nghỉ bù cả ngày', 'requires_full_day_shift': False, 'is_compensatory': True},
    {'name': 'Nghỉ bù nửa ngày', 'requires_full_day_shift': True, 'is_compensatory': True},
]

# Trong handle(), cập nhật save:
for i, data in enumerate(DEFAULTS, start=1):
    obj, created = ExplanationReason.objects.get_or_create(
        name=data['name'],
        defaults={
            'order': i,
            'requires_full_day_shift': data['requires_full_day_shift'],
            'is_compensatory': data['is_compensatory'],
        },
    )
    if not created:
        obj.requires_full_day_shift = data['requires_full_day_shift']
        obj.is_compensatory = data['is_compensatory']
        obj.order = i
        obj.save()
```

**Step 5: Tạo migration**

```bash
python manage.py makemigrations explanations --name add_is_compensatory_to_reason
```
Expected: `explanations/migrations/000X_add_is_compensatory_to_reason.py` created

**Step 6: Apply migration**

```bash
python manage.py migrate
```

**Step 7: Chạy test để xác nhận pass**

```bash
pytest explanations/tests/test_models.py -v
```
Expected: tất cả PASS

**Step 8: Commit**

```bash
git add explanations/models.py explanations/management/commands/seed_explanation_reasons.py explanations/migrations/ explanations/tests/test_models.py
git commit -m "feat: add is_compensatory to ExplanationReason, seed nghỉ bù reasons"
```

---

## Task 2: Thêm `ci_use_compensatory` / `co_use_compensatory` vào Explanation

**Files:**
- Modify: `explanations/models.py`
- Test: `explanations/tests/test_models.py`

**Step 1: Viết test**

```python
# explanations/tests/test_models.py — thêm vào cuối

@pytest.mark.django_db
def test_explanation_compensatory_flags_default_false(db):
    from attendance.models import AttendanceRecord, AttendanceUpload
    from employees.models import Employee, Department
    from accounts.models import User
    user = User.objects.create_user(email='e@e.com', password='pass')
    dept = Department.objects.create(name='D')
    emp = Employee.objects.create(user=user, code='E01', full_name='E', department=dept)
    hr = User.objects.create_user(email='hr@e.com', password='pass')
    upload = AttendanceUpload.objects.create(month='2026-05', uploaded_by=hr, status='done')
    record = AttendanceRecord.objects.create(
        upload=upload, employee=emp, date='2026-05-01', error_types=[]
    )
    exp = Explanation.objects.create(record=record, employee=emp)
    assert exp.ci_use_compensatory is False
    assert exp.co_use_compensatory is False
```

**Step 2: Chạy test để xác nhận fail**

```bash
pytest explanations/tests/test_models.py::test_explanation_compensatory_flags_default_false -v
```

**Step 3: Thêm 2 field vào `Explanation`**

Trong `explanations/models.py`, thêm vào class `Explanation` sau field `co_reviewer_note`:
```python
    # --- Compensatory flags ---
    ci_use_compensatory = models.BooleanField(default=False)
    co_use_compensatory = models.BooleanField(default=False)
```

**Step 4: Tạo và apply migration**

```bash
python manage.py makemigrations explanations --name add_use_compensatory_to_explanation
python manage.py migrate
```

**Step 5: Chạy test**

```bash
pytest explanations/tests/test_models.py -v
```
Expected: tất cả PASS

**Step 6: Commit**

```bash
git add explanations/models.py explanations/migrations/ explanations/tests/test_models.py
git commit -m "feat: add ci_use_compensatory/co_use_compensatory to Explanation"
```

---

## Task 3: Thêm CompensatoryBalance + CompensatoryTransaction models

**Files:**
- Modify: `employees/models.py`
- Modify: `employees/admin.py`
- Create: `employees/tests/test_compensatory_models.py`

**Step 1: Viết test**

```python
# employees/tests/test_compensatory_models.py (file mới)
import pytest
from decimal import Decimal
from datetime import date
from employees.models import Department, Employee, CompensatoryBalance, CompensatoryTransaction
from accounts.models import User


@pytest.fixture
def employee(db):
    user = User.objects.create_user(email='emp@e.com', password='pass')
    dept = Department.objects.create(name='KD')
    return Employee.objects.create(user=user, code='NV001', full_name='A', department=dept)


@pytest.mark.django_db
def test_compensatory_balance_created(employee):
    bal = CompensatoryBalance.objects.create(employee=employee)
    assert bal.total_hours == 0
    assert bal.used_hours == 0
    assert bal.remaining_hours == Decimal('0')


@pytest.mark.django_db
def test_compensatory_balance_remaining(employee):
    bal = CompensatoryBalance.objects.create(employee=employee, total_hours=8, used_hours=3)
    assert bal.remaining_hours == Decimal('5')


@pytest.mark.django_db
def test_compensatory_transaction_credit(employee):
    bal = CompensatoryBalance.objects.create(employee=employee, total_hours=0)
    hr = User.objects.create_user(email='hr@e.com', password='pass')
    t = CompensatoryTransaction.objects.create(
        employee=employee, balance=bal,
        transaction_type=CompensatoryTransaction.Type.CREDIT,
        hours=Decimal('8'), date=date(2026, 5, 1),
        note='Làm thêm thứ 7', created_by=hr,
    )
    assert t.hours == Decimal('8')
    assert t.transaction_type == 'credit'


@pytest.mark.django_db
def test_compensatory_balance_one_to_one(employee):
    CompensatoryBalance.objects.create(employee=employee)
    with pytest.raises(Exception):
        CompensatoryBalance.objects.create(employee=employee)
```

**Step 2: Chạy test để xác nhận fail**

```bash
pytest employees/tests/test_compensatory_models.py -v
```
Expected: FAIL với `ImportError: cannot import name 'CompensatoryBalance'`

**Step 3: Thêm models vào `employees/models.py`**

Thêm vào cuối file sau class `LeaveTransaction`:

```python
class CompensatoryBalance(models.Model):
    employee = models.OneToOneField(
        Employee, on_delete=models.CASCADE, related_name='compensatory_balance'
    )
    total_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    used_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    @property
    def remaining_hours(self):
        return self.total_hours - self.used_hours

    class Meta:
        verbose_name = 'Số giờ nghỉ bù'

    def __str__(self):
        return f'{self.employee.code} - bù còn {self.remaining_hours}h'


class CompensatoryTransaction(models.Model):
    class Type(models.TextChoices):
        CREDIT = 'credit', 'Cấp bù'
        DEBIT = 'debit', 'Dùng bù'

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='compensatory_transactions'
    )
    balance = models.ForeignKey(
        CompensatoryBalance, on_delete=models.CASCADE, related_name='transactions'
    )
    transaction_type = models.CharField(max_length=10, choices=Type.choices)
    hours = models.DecimalField(max_digits=4, decimal_places=1)
    date = models.DateField()
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='compensatory_created'
    )
    explanation = models.OneToOneField(
        'explanations.Explanation', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='compensatory_transaction'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Giao dịch nghỉ bù'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.employee.code} {self.transaction_type} {self.hours}h {self.date}'
```

**Step 4: Đăng ký admin**

Trong `employees/admin.py`, thêm import và 2 class:
```python
from .models import Department, Employee, LeaveBalance, LeaveTransaction, CompensatoryBalance, CompensatoryTransaction

@admin.register(CompensatoryBalance)
class CompensatoryBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'total_hours', 'used_hours', 'remaining_hours']
    search_fields = ['employee__code', 'employee__full_name']

@admin.register(CompensatoryTransaction)
class CompensatoryTransactionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'transaction_type', 'hours', 'date', 'created_by']
    list_filter = ['transaction_type']
```

**Step 5: Tạo và apply migration**

```bash
python manage.py makemigrations employees --name add_compensatory_balance_transaction
python manage.py migrate
```

**Step 6: Chạy test**

```bash
pytest employees/tests/test_compensatory_models.py -v
```
Expected: tất cả PASS

**Step 7: Commit**

```bash
git add employees/models.py employees/admin.py employees/migrations/ employees/tests/test_compensatory_models.py
git commit -m "feat: add CompensatoryBalance and CompensatoryTransaction models"
```

---

## Task 4: Cập nhật `compute_record_hours` trả về 3-tuple + routing nghỉ bù

**Files:**
- Modify: `reports/calculator.py`
- Modify: `reports/exporter.py`
- Modify: `reports/tests/test_calculator.py`

**Step 1: Cập nhật tất cả callers trong test hiện tại**

Trong `reports/tests/test_calculator.py`, tìm tất cả dòng `w, l = compute_record_hours(...)` và thay thành `w, l, c = compute_record_hours(...)`. Đây là các test cần cập nhật:
- `test_ok_record_full_hours`
- `test_late_approved_phep`
- `test_late_unpaid`
- `test_missing_in_no_explanation_block_unpaid`
- `test_missing_in_phep2`
- `test_missing_in_approved_cong`
- `test_early_leave_unpaid`
- `test_absent_unpaid`
- `test_qcc_lần_1_no_split`
- `test_qcc_lần_3_split_50_50`

Thêm `assert c == 0.0` vào mỗi test trên (không có compensatory ở đây).

**Step 2: Thêm các test mới cho compensatory**

Thêm vào cuối `reports/tests/test_calculator.py`:

```python
def _comp_reason(name, full_day=False):
    return ExplanationReason.objects.create(
        name=name, requires_full_day_shift=full_day, is_compensatory=True
    )


@pytest.mark.django_db
def test_missing_in_nghi_bu_nua_ngay(base):
    """Nghỉ bù nửa ngày → work -4h, leave 0, compensatory +4h"""
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['MISSING_IN'])
    reason = _comp_reason('Nghỉ bù nửa ngày', full_day=True)
    exp = _explanation(record, base['emp'], ci_reason=reason, ci_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 4.0
    assert l == 0.0
    assert c == 4.0


@pytest.mark.django_db
def test_absent_nghi_bu_ca_ngay(base):
    """Nghỉ bù cả ngày → work 0, leave 0, compensatory 8h"""
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['ABSENT'])
    reason = _comp_reason('Nghỉ bù cả ngày')
    exp = _explanation(record, base['emp'],
                       ci_reason=reason, ci_status='approved',
                       co_reason=reason, co_status='approved')
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 0.0
    assert l == 0.0
    assert c == 8.0


@pytest.mark.django_db
def test_late_phep_with_use_compensatory_checkbox(base):
    """Đi muộn 30p, lý do 'Đi muộn/ Về sớm', tick use_compensatory → trừ bù thay phép"""
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['LATE'], minutes_late=30)
    reason = _reason('Đi muộn/ Về sớm')
    exp = Explanation.objects.create(
        record=record, employee=base['emp'],
        ci_reason=reason, ci_status='approved',
        ci_use_compensatory=True,
    )
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 7.5
    assert l == 0.0
    assert c == 0.5


@pytest.mark.django_db
def test_missing_in_phep_nua_ngay_use_compensatory(base):
    """Nghỉ phép nửa ngày nhưng tick use_compensatory → route sang bù"""
    shift = base['shift']
    record = _record(base['upload'], base['emp'], 1, ['MISSING_IN'])
    reason = _reason('Nghỉ phép nửa ngày', full_day=True)
    exp = Explanation.objects.create(
        record=record, employee=base['emp'],
        ci_reason=reason, ci_status='approved',
        ci_use_compensatory=True,
    )
    w, l, c = compute_record_hours(record, exp, shift, 0)
    assert w == 4.0
    assert l == 0.0
    assert c == 4.0
```

**Step 3: Chạy test để xác nhận fail**

```bash
pytest reports/tests/test_calculator.py -v -x
```
Expected: FAIL vì `compute_record_hours` vẫn trả về 2-tuple

**Step 4: Cập nhật `compute_record_hours` trong `reports/calculator.py`**

Thay toàn bộ hàm `compute_record_hours` (từ `def compute_record_hours(` đến kết thúc hàm) bằng:

```python
def compute_record_hours(record, exp, shift, qcc_count):
    """
    Compute (work_hours, leave_hours, compensatory_hours) for a single attendance record.
    """
    error_set = set(record.error_types)
    base_work = float(shift.work_hours) if shift else 8.0
    base_leave = float(shift.leave_hours) if shift else 0.0

    if not error_set:
        return base_work, base_leave, 0.0

    ci_reason = exp.ci_reason if exp else None
    co_reason = exp.co_reason if exp else None
    ci_approved = bool(exp and exp.ci_status == Explanation.Status.APPROVED)
    co_approved = bool(exp and exp.co_status == Explanation.Status.APPROVED)
    ci_use_comp = bool(exp and exp.ci_use_compensatory)
    co_use_comp = bool(exp and exp.co_use_compensatory)

    if 'ABSENT' in error_set:
        reason = ci_reason or co_reason
        approved = ci_approved or co_approved
        if approved and reason:
            if reason.is_compensatory:
                return 0.0, 0.0, base_work
            if reason.name in LEAVE_FULL_DAY_REASONS:
                return 0.0, base_work, 0.0
            if reason.name in UNPAID_REASONS:
                return 0.0, 0.0, 0.0
            if reason.name in EXCUSED_REASONS:
                if _is_qcc_record(exp) and qcc_count >= 3:
                    half = round(base_work / 2, 2)
                    return half, half, 0.0
                return base_work, base_leave, 0.0
        return 0.0, 0.0, 0.0

    result_ci = _ci_result(error_set, ci_reason, ci_approved)
    result_co = _co_result(error_set, co_reason, co_approved)

    if result_ci == RC.UNPAID_BLOCK and result_co == RC.UNPAID_BLOCK:
        return 0.0, 0.0, 0.0

    if result_ci == RC.DAY_OFF and result_co == RC.DAY_OFF:
        ci_comp = ci_reason and ci_reason.is_compensatory
        co_comp = co_reason and co_reason.is_compensatory
        if ci_comp or co_comp:
            return 0.0, 0.0, base_work
        ci_leave = ci_reason and ci_reason.name in LEAVE_FULL_DAY_REASONS
        co_leave = co_reason and co_reason.name in LEAVE_FULL_DAY_REASONS
        if ci_leave or co_leave:
            return 0.0, base_work, 0.0
        return 0.0, 0.0, 0.0

    d_work_ci, d_leave_ci = _apply_adj(result_ci, record.minutes_late, shift, 'morning')
    d_work_co, d_leave_co = _apply_adj(result_co, record.minutes_early, shift, 'afternoon')

    comp = 0.0
    if (ci_use_comp or (ci_reason and ci_reason.is_compensatory)) and d_leave_ci > 0:
        comp += d_leave_ci
        d_leave_ci = 0.0
    if (co_use_comp or (co_reason and co_reason.is_compensatory)) and d_leave_co > 0:
        comp += d_leave_co
        d_leave_co = 0.0

    work = base_work + d_work_ci + d_work_co
    leave = base_leave + d_leave_ci + d_leave_co

    if result_ci == RC.LEAVE_BLOCK and record.minutes_late and shift:
        overflow = record.minutes_late - _morning_block_hours(shift) * 60 - _break_minutes(shift)
        if overflow > 0:
            work -= overflow / 60
            if ci_use_comp or (ci_reason and ci_reason.is_compensatory):
                comp += overflow / 60
            else:
                leave += overflow / 60

    if result_co == RC.LEAVE_BLOCK and record.minutes_early and shift:
        overflow = record.minutes_early - _afternoon_block_hours(shift) * 60 - _break_minutes(shift)
        if overflow > 0:
            work -= overflow / 60
            if co_use_comp or (co_reason and co_reason.is_compensatory):
                comp += overflow / 60
            else:
                leave += overflow / 60

    work = max(work, 0.0)

    if _is_qcc_record(exp) and qcc_count >= 3:
        half = round(work / 2, 2)
        leave += half
        work = half

    return round(work, 2), round(leave, 2), round(comp, 2)
```

Cũng cần thêm vào calculator 2 set constants (sau UNPAID_REASONS):
```python
COMPENSATORY_FULL_DAY_REASONS = {'Nghỉ bù cả ngày'}
COMPENSATORY_HALF_DAY_REASONS = {'Nghỉ bù nửa ngày'}
```

Và trong `_ci_result` / `_co_result`, thêm xử lý cho reason is_compensatory → return LEAVE_BLOCK/DAY_OFF (tương tự phép):

Trong `_ci_result`, thêm sau `if rn in LEAVE_HALF_DAY_REASONS:`:
```python
    if ci_reason and ci_reason.is_compensatory:
        if ci_reason.requires_full_day_shift:
            return RC.LEAVE_BLOCK
        return RC.DAY_OFF
```

Tương tự trong `_co_result`.

**Step 5: Cập nhật `reports/exporter.py` line 66**

Thay `w, l = compute_record_hours(record, exp, shift, qcc_count)` thành:
```python
w, l, _c = compute_record_hours(record, exp, shift, qcc_count)
```

**Step 6: Chạy toàn bộ test**

```bash
pytest reports/tests/test_calculator.py -v
```
Expected: tất cả PASS

**Step 7: Commit**

```bash
git add reports/calculator.py reports/exporter.py reports/tests/test_calculator.py
git commit -m "feat: compute_record_hours returns 3-tuple, route compensatory hours"
```

---

## Task 5: Cập nhật `calculate_month` — running balance + tạo CompensatoryTransaction

**Files:**
- Modify: `reports/calculator.py`
- Modify: `reports/tests/test_calculator.py`

**Step 1: Thêm test integration cho compensatory**

Thêm vào cuối `reports/tests/test_calculator.py`:

```python
from employees.models import CompensatoryBalance, CompensatoryTransaction


@pytest.mark.django_db
def test_calculate_month_creates_compensatory_transaction(base):
    """Khi tính lương, giờ bù được debit vào CompensatoryBalance"""
    s = base
    bal = CompensatoryBalance.objects.create(employee=s['emp'], total_hours=8, used_hours=0)
    record = _record(s['upload'], s['emp'], 1, ['ABSENT'])
    reason = ExplanationReason.objects.create(name='Nghỉ bù cả ngày', is_compensatory=True)
    _explanation(record, s['emp'], ci_reason=reason, ci_status='approved',
                 co_reason=reason, co_status='approved')
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert float(calc.work_hours) == 0.0
    assert float(calc.leave_hours) == 0.0
    bal.refresh_from_db()
    assert float(bal.used_hours) == 8.0
    assert CompensatoryTransaction.objects.filter(
        employee=s['emp'], transaction_type='debit'
    ).exists()


@pytest.mark.django_db
def test_calculate_month_fallback_when_comp_balance_insufficient(base):
    """Nếu giờ bù không đủ, fallback: không trừ phép cũng không trừ bù"""
    s = base
    CompensatoryBalance.objects.create(employee=s['emp'], total_hours=2, used_hours=0)
    record = _record(s['upload'], s['emp'], 1, ['ABSENT'])
    reason = ExplanationReason.objects.create(name='Nghỉ bù cả ngày', is_compensatory=True)
    _explanation(record, s['emp'], ci_reason=reason, ci_status='approved',
                 co_reason=reason, co_status='approved')
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    # 8h bù yêu cầu nhưng chỉ có 2h → fallback: treat as excused, work = 8
    assert float(calc.work_hours) == 8.0
    assert float(calc.leave_hours) == 0.0


@pytest.mark.django_db
def test_calculate_month_fallback_when_leave_balance_insufficient(base):
    """Nếu phép không đủ, fallback: không trừ phép"""
    s = base
    LeaveBalance.objects.create(employee=s['emp'], year=2026, total_days=0)
    record = _record(s['upload'], s['emp'], 1, ['ABSENT'])
    reason = ExplanationReason.objects.create(name='Nghỉ phép cả ngày')
    _explanation(record, s['emp'], ci_reason=reason, ci_status='approved',
                 co_reason=reason, co_status='approved')
    result = calculate_month(month='2026-05', calculated_by=s['hr'])
    calc = result[s['emp'].code]
    assert float(calc.leave_hours) == 0.0
```

**Step 2: Chạy test để xác nhận fail**

```bash
pytest reports/tests/test_calculator.py::test_calculate_month_creates_compensatory_transaction -v
```
Expected: FAIL

**Step 3: Cập nhật `calculate_month` trong `reports/calculator.py`**

Thêm import ở đầu file:
```python
from employees.models import Employee, CompensatoryBalance, CompensatoryTransaction
```
(Thay thế import `from employees.models import Employee` hiện tại)

Trong hàm `calculate_month`, thay đoạn vòng lặp per-employee hiện tại bằng:

```python
    calcs = {}
    for code, emp_records in by_employee.items():
        emp = emp_records[0].employee
        total_work = 0.0
        total_leave = 0.0
        total_compensatory = 0.0
        qcc_count = 0

        lb = LeaveBalance.objects.filter(
            employee=emp, year=int(month[:4])
        ).first()
        running_leave_remaining = float(lb.remaining_days * 8) if lb else 0.0
        comp_balance, _ = CompensatoryBalance.objects.get_or_create(employee=emp)
        running_comp_remaining = float(comp_balance.remaining_hours)

        for record in emp_records:
            exp = getattr(record, 'explanation', None)
            shift = shift_map.get(record.shift_code) if record.shift_code else None

            if _is_qcc_record(exp):
                qcc_count += 1

            w, l, c = compute_record_hours(record, exp, shift, qcc_count)

            if c > 0 and running_comp_remaining - c < 0:
                l = 0.0
                c = 0.0

            if l > 0 and running_leave_remaining - l < 0:
                l = 0.0

            running_comp_remaining -= c
            running_leave_remaining -= l
            total_work += w
            total_leave += l
            total_compensatory += c

        total_work = round(total_work, 2)
        total_leave = round(total_leave, 2)
        total_compensatory = round(total_compensatory, 2)

        calc, _ = AttendanceCalculation.objects.update_or_create(
            employee=emp,
            month=month,
            defaults={
                'work_hours': Decimal(str(total_work)),
                'leave_hours': Decimal(str(total_leave)),
                'actual_workdays': Decimal(str(round(total_work / 8, 2))),
                'leave_days_used': Decimal(str(round(total_leave / 8, 2))),
                'calculated_by': calculated_by,
                'status': AttendanceCalculation.Status.DRAFT,
            }
        )

        if total_compensatory > 0:
            comp_balance.used_hours = Decimal(str(
                float(comp_balance.used_hours) + total_compensatory
            ))
            comp_balance.save()
            import calendar
            last_day = calendar.monthrange(int(month[:4]), int(month[5:]))[1]
            from datetime import date as _date
            CompensatoryTransaction.objects.create(
                employee=emp,
                balance=comp_balance,
                transaction_type=CompensatoryTransaction.Type.DEBIT,
                hours=Decimal(str(total_compensatory)),
                date=_date(int(month[:4]), int(month[5:]), last_day),
                note=f'Tính công tháng {month}',
                created_by=calculated_by,
            )

        calcs[code] = calc

    return calcs
```

Lưu ý: thêm `from employees.models import LeaveBalance` vào imports nếu chưa có (hiện tại đã import qua `from employees.models import Employee`).

**Step 4: Chạy test**

```bash
pytest reports/tests/test_calculator.py -v
```
Expected: tất cả PASS

**Step 5: Chạy toàn bộ test suite**

```bash
make test
```
Expected: tất cả PASS

**Step 6: Commit**

```bash
git add reports/calculator.py reports/tests/test_calculator.py
git commit -m "feat: calculate_month tracks compensatory balance, creates CompensatoryTransaction"
```

---

## Task 6: Màn hình NV — "Phép & Nghỉ bù của tôi"

**Files:**
- Modify: `employees/views.py`
- Modify: `employees/urls.py`
- Create: `templates/employees/my_leave.html`
- Test: `employees/tests/test_views.py`

**Step 1: Viết test**

Mở `employees/tests/test_views.py`, thêm vào cuối:

```python
@pytest.mark.django_db
def test_my_leave_view_employee(client):
    from employees.models import CompensatoryBalance, CompensatoryTransaction
    from datetime import date
    user = User.objects.create_user(email='emp@e.com', password='pass')
    dept = Department.objects.create(name='KD')
    emp = Employee.objects.create(user=user, code='E01', full_name='E', department=dept)
    lb = LeaveBalance.objects.create(employee=emp, year=2026, total_days=12)
    bal = CompensatoryBalance.objects.create(employee=emp, total_hours=8)
    client.force_login(user)
    resp = client.get('/employees/my-leave/')
    assert resp.status_code == 200
    assert b'12' in resp.content   # total_days
    assert b'8' in resp.content    # total_hours


@pytest.mark.django_db
def test_my_leave_view_hr_redirected(client):
    user = User.objects.create_user(email='hr@e.com', password='pass', role='HR')
    client.force_login(user)
    resp = client.get('/employees/my-leave/')
    assert resp.status_code == 302
```

**Step 2: Chạy test để xác nhận fail**

```bash
pytest employees/tests/test_views.py::test_my_leave_view_employee -v
```
Expected: FAIL với 404

**Step 3: Thêm view vào `employees/views.py`**

Thêm import ở đầu:
```python
from .models import Employee, Department, LeaveBalance, CompensatoryBalance, CompensatoryTransaction
```

Thêm view mới sau `leave_balance_view`:
```python
@login_required
def my_leave_view(request):
    if _hr_only(request):
        return redirect('employees:list')
    try:
        emp = request.user.employee_profile
    except Employee.DoesNotExist:
        return render(request, 'attendance/no_profile.html')

    leave_balances = LeaveBalance.objects.filter(employee=emp).order_by('-year')
    comp_balance, _ = CompensatoryBalance.objects.get_or_create(employee=emp)
    comp_transactions = CompensatoryTransaction.objects.filter(
        employee=emp
    ).select_related('created_by').order_by('-date', '-created_at')[:50]

    year_filter = request.GET.get('year', str(2026))
    leave_transactions = emp.leave_transactions.filter(
        month__startswith=year_filter
    ).order_by('-date')[:50]

    return render(request, 'employees/my_leave.html', {
        'emp': emp,
        'leave_balances': leave_balances,
        'comp_balance': comp_balance,
        'comp_transactions': comp_transactions,
        'leave_transactions': leave_transactions,
        'year_filter': year_filter,
    })
```

**Step 4: Thêm URL**

Trong `employees/urls.py`, thêm:
```python
path('my-leave/', views.my_leave_view, name='my_leave'),
```

**Step 5: Tạo template `templates/employees/my_leave.html`**

```html
{% extends "base/base.html" %}
{% block title %}Phép & Nghỉ bù của tôi{% endblock %}
{% block content %}
<h4 class="mb-3"><i class="bi bi-calendar3"></i> Phép & Nghỉ bù — {{ emp.full_name }}</h4>

<div class="row g-3 mb-4">
  <div class="col-12 col-md-6">
    <div class="card border-primary h-100">
      <div class="card-header bg-primary text-white fw-bold">Ngày phép</div>
      <div class="card-body">
        {% for lb in leave_balances %}
        <div class="d-flex justify-content-between mb-1">
          <span>Năm {{ lb.year }}</span>
          <span>
            <span class="text-muted">Tổng {{ lb.total_days }}d /</span>
            Đã dùng {{ lb.used_days }}d /
            <strong class="text-success">Còn {{ lb.remaining_days }}d</strong>
          </span>
        </div>
        {% empty %}
        <p class="text-muted mb-0">Chưa có dữ liệu phép.</p>
        {% endfor %}
      </div>
    </div>
  </div>
  <div class="col-12 col-md-6">
    <div class="card border-warning h-100">
      <div class="card-header bg-warning fw-bold">Giờ nghỉ bù</div>
      <div class="card-body">
        <div class="d-flex justify-content-between mb-1">
          <span>Tổng được cấp</span><strong>{{ comp_balance.total_hours }}h</strong>
        </div>
        <div class="d-flex justify-content-between mb-1">
          <span>Đã dùng</span><strong>{{ comp_balance.used_hours }}h</strong>
        </div>
        <div class="d-flex justify-content-between">
          <span>Còn lại</span>
          <strong class="text-success fs-5">{{ comp_balance.remaining_hours }}h</strong>
        </div>
      </div>
    </div>
  </div>
</div>

<ul class="nav nav-tabs mb-3" id="leaveTabs">
  <li class="nav-item">
    <a class="nav-link active" data-bs-toggle="tab" href="#tab-comp">Lịch sử nghỉ bù</a>
  </li>
  <li class="nav-item">
    <a class="nav-link" data-bs-toggle="tab" href="#tab-leave">Lịch sử phép</a>
  </li>
</ul>

<div class="tab-content">
  <div class="tab-pane fade show active" id="tab-comp">
    <table class="table table-bordered table-sm">
      <thead class="table-light">
        <tr><th>Ngày</th><th>Loại</th><th>Giờ</th><th>Ghi chú</th></tr>
      </thead>
      <tbody>
        {% for t in comp_transactions %}
        <tr>
          <td>{{ t.date }}</td>
          <td>
            {% if t.transaction_type == 'credit' %}
            <span class="badge bg-success">Cấp</span>
            {% else %}
            <span class="badge bg-secondary">Dùng</span>
            {% endif %}
          </td>
          <td>{{ t.hours }}h</td>
          <td>{{ t.note }}</td>
        </tr>
        {% empty %}
        <tr><td colspan="4" class="text-center text-muted">Chưa có giao dịch.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="tab-pane fade" id="tab-leave">
    <form method="get" class="d-flex gap-2 mb-2">
      <input type="number" name="year" value="{{ year_filter }}" class="form-control form-control-sm" style="width:100px">
      <button class="btn btn-sm btn-outline-secondary">Lọc</button>
    </form>
    <table class="table table-bordered table-sm">
      <thead class="table-light">
        <tr><th>Tháng</th><th>Ngày</th><th>Số ngày</th><th>Ghi chú</th></tr>
      </thead>
      <tbody>
        {% for t in leave_transactions %}
        <tr>
          <td>{{ t.month }}</td>
          <td>{{ t.date }}</td>
          <td>{{ t.days }}d</td>
          <td>{{ t.note }}</td>
        </tr>
        {% empty %}
        <tr><td colspan="4" class="text-center text-muted">Chưa có giao dịch.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

**Step 6: Chạy test**

```bash
pytest employees/tests/test_views.py -v
```
Expected: tất cả PASS

**Step 7: Commit**

```bash
git add employees/views.py employees/urls.py templates/employees/my_leave.html employees/tests/test_views.py
git commit -m "feat: employee my-leave view showing leave and compensatory balance"
```

---

## Task 7: Màn hình HR — Quản lý phép & nghỉ bù

**Files:**
- Modify: `employees/views.py`
- Modify: `employees/urls.py`
- Modify: `employees/forms.py`
- Create: `templates/employees/leave_management.html`
- Create: `templates/employees/compensatory_credit.html`

**Step 1: Thêm form vào `employees/forms.py`**

```python
from .models import Employee, LeaveBalance, CompensatoryBalance

class CompensatoryCreditForm(forms.Form):
    hours = forms.DecimalField(
        max_digits=4, decimal_places=1, min_value=Decimal('0.5'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        label='Số giờ cấp bù'
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Ngày'
    )
    note = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Ghi chú', required=False
    )
```

Thêm `from decimal import Decimal` ở đầu forms.py nếu chưa có.

**Step 2: Thêm views vào `employees/views.py`**

```python
from .forms import EmployeeForm, LeaveBalanceForm, CompensatoryCreditForm
from decimal import Decimal
import openpyxl
from django.http import HttpResponse

@login_required
def leave_management(request):
    if not _hr_only(request):
        return redirect('attendance:my_attendance')
    dept_id = request.GET.get('dept')
    employees = Employee.objects.select_related(
        'department', 'compensatory_balance'
    ).prefetch_related('leave_balances').filter(is_active=True)
    if dept_id:
        employees = employees.filter(department_id=dept_id)
    employees = employees.order_by('code')

    # Attach current year leave balance
    current_year = 2026
    emp_data = []
    for emp in employees:
        lb = emp.leave_balances.filter(year=current_year).first()
        cb = getattr(emp, 'compensatory_balance', None)
        emp_data.append({'emp': emp, 'lb': lb, 'cb': cb})

    departments = Department.objects.all()

    if 'export' in request.GET:
        return _export_leave_management(emp_data, current_year)

    return render(request, 'employees/leave_management.html', {
        'emp_data': emp_data,
        'departments': departments,
        'dept_id': dept_id,
        'current_year': current_year,
    })


def _export_leave_management(emp_data, year):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f'Phep_Bu_{year}'
    ws.append(['Mã NV', 'Họ tên', 'Phòng ban',
               f'Phép tổng {year}', f'Phép đã dùng', 'Phép còn lại',
               'Bù tổng (h)', 'Bù đã dùng (h)', 'Bù còn lại (h)'])
    for item in emp_data:
        emp, lb, cb = item['emp'], item['lb'], item['cb']
        ws.append([
            emp.code, emp.full_name, emp.department.name,
            float(lb.total_days) if lb else 0,
            float(lb.used_days) if lb else 0,
            float(lb.remaining_days) if lb else 0,
            float(cb.total_hours) if cb else 0,
            float(cb.used_hours) if cb else 0,
            float(cb.remaining_hours) if cb else 0,
        ])
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="phep_bu_{year}.xlsx"'
    wb.save(response)
    return response


@login_required
def compensatory_credit(request, emp_pk):
    if not _hr_only(request):
        return redirect('attendance:my_attendance')
    emp = get_object_or_404(Employee, pk=emp_pk)
    comp_balance, _ = CompensatoryBalance.objects.get_or_create(employee=emp)
    transactions = CompensatoryTransaction.objects.filter(
        employee=emp
    ).order_by('-date', '-created_at')[:30]

    if request.method == 'POST':
        form = CompensatoryCreditForm(request.POST)
        if form.is_valid():
            hours = form.cleaned_data['hours']
            comp_balance.total_hours += hours
            comp_balance.save()
            CompensatoryTransaction.objects.create(
                employee=emp,
                balance=comp_balance,
                transaction_type=CompensatoryTransaction.Type.CREDIT,
                hours=hours,
                date=form.cleaned_data['date'],
                note=form.cleaned_data.get('note', ''),
                created_by=request.user,
            )
            messages.success(request, f'Đã cấp {hours}h nghỉ bù cho {emp.full_name}.')
            return redirect('employees:compensatory_credit', emp_pk=emp_pk)
    else:
        form = CompensatoryCreditForm()

    return render(request, 'employees/compensatory_credit.html', {
        'emp': emp,
        'comp_balance': comp_balance,
        'form': form,
        'transactions': transactions,
    })
```

Thêm import `from .models import Employee, Department, LeaveBalance, CompensatoryBalance, CompensatoryTransaction`.

**Step 3: Thêm URLs**

Trong `employees/urls.py`:
```python
path('leave-management/', views.leave_management, name='leave_management'),
path('<int:emp_pk>/compensatory/', views.compensatory_credit, name='compensatory_credit'),
```

**Step 4: Tạo template `templates/employees/leave_management.html`**

```html
{% extends "base/base.html" %}
{% block title %}Quản lý phép & nghỉ bù{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h4><i class="bi bi-calendar2-week"></i> Quản lý phép & nghỉ bù {{ current_year }}</h4>
  <a href="?{% if dept_id %}dept={{ dept_id }}&{% endif %}export=1" class="btn btn-success btn-sm">
    <i class="bi bi-download"></i> Export Excel
  </a>
</div>

<form method="get" class="d-flex gap-2 mb-3">
  <select name="dept" class="form-select form-select-sm" style="width:200px">
    <option value="">Tất cả phòng ban</option>
    {% for d in departments %}
    <option value="{{ d.pk }}" {% if dept_id == d.pk|stringformat:"s" %}selected{% endif %}>{{ d.name }}</option>
    {% endfor %}
  </select>
  <button class="btn btn-sm btn-outline-secondary">Lọc</button>
</form>

<table class="table table-bordered table-sm table-hover">
  <thead class="table-light">
    <tr>
      <th>Mã NV</th><th>Họ tên</th><th>Phòng ban</th>
      <th>Phép còn lại</th><th>Bù còn lại (h)</th><th></th>
    </tr>
  </thead>
  <tbody>
    {% for item in emp_data %}
    <tr>
      <td>{{ item.emp.code }}</td>
      <td>{{ item.emp.full_name }}</td>
      <td>{{ item.emp.department.name }}</td>
      <td>
        {% if item.lb %}
          <span class="{% if item.lb.remaining_days <= 0 %}text-danger{% endif %}">
            {{ item.lb.remaining_days }}d
          </span>
          <small class="text-muted">({{ item.lb.used_days }}/{{ item.lb.total_days }})</small>
        {% else %}—{% endif %}
      </td>
      <td>
        {% if item.cb %}
          <span class="{% if item.cb.remaining_hours <= 0 %}text-danger{% endif %}">
            {{ item.cb.remaining_hours }}h
          </span>
          <small class="text-muted">({{ item.cb.used_hours }}/{{ item.cb.total_hours }})</small>
        {% else %}—{% endif %}
      </td>
      <td>
        <a href="{% url 'employees:compensatory_credit' item.emp.pk %}" class="btn btn-sm btn-outline-primary">
          <i class="bi bi-plus-circle"></i> Cấp bù
        </a>
        <a href="{% url 'employees:leave_balance' item.emp.pk %}" class="btn btn-sm btn-outline-secondary">Phép</a>
      </td>
    </tr>
    {% empty %}
    <tr><td colspan="6" class="text-center text-muted">Không có nhân viên.</td></tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

**Step 5: Tạo template `templates/employees/compensatory_credit.html`**

```html
{% extends "base/base.html" %}
{% block title %}Cấp giờ bù — {{ emp.full_name }}{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h4><i class="bi bi-clock-history"></i> Nghỉ bù — {{ emp.full_name }} ({{ emp.code }})</h4>
  <a href="{% url 'employees:leave_management' %}" class="btn btn-outline-secondary btn-sm">← Quay lại</a>
</div>

<div class="row mb-3">
  <div class="col-auto">
    <div class="card border-warning px-4 py-2 text-center">
      <div class="text-muted small">Còn lại</div>
      <div class="fs-3 fw-bold text-warning">{{ comp_balance.remaining_hours }}h</div>
      <div class="text-muted small">Tổng {{ comp_balance.total_hours }}h / Đã dùng {{ comp_balance.used_hours }}h</div>
    </div>
  </div>
</div>

<div class="row">
  <div class="col-12 col-md-5">
    <div class="card shadow-sm mb-3">
      <div class="card-header bg-primary text-white fw-bold">Cấp giờ bù mới</div>
      <div class="card-body">
        <form method="post">
          {% csrf_token %}
          <div class="mb-2">
            <label class="form-label">{{ form.hours.label }}</label>
            {{ form.hours }}
          </div>
          <div class="mb-2">
            <label class="form-label">{{ form.date.label }}</label>
            {{ form.date }}
          </div>
          <div class="mb-3">
            <label class="form-label">{{ form.note.label }}</label>
            {{ form.note }}
          </div>
          <button type="submit" class="btn btn-primary w-100">Cấp bù</button>
        </form>
      </div>
    </div>
  </div>
  <div class="col-12 col-md-7">
    <h6>Lịch sử giao dịch</h6>
    <table class="table table-sm table-bordered">
      <thead class="table-light">
        <tr><th>Ngày</th><th>Loại</th><th>Giờ</th><th>Ghi chú</th><th>Người tạo</th></tr>
      </thead>
      <tbody>
        {% for t in transactions %}
        <tr>
          <td>{{ t.date }}</td>
          <td>
            {% if t.transaction_type == 'credit' %}
            <span class="badge bg-success">Cấp</span>
            {% else %}
            <span class="badge bg-secondary">Dùng</span>
            {% endif %}
          </td>
          <td>{{ t.hours }}h</td>
          <td>{{ t.note }}</td>
          <td>{{ t.created_by.email|default:"—" }}</td>
        </tr>
        {% empty %}
        <tr><td colspan="5" class="text-center text-muted">Chưa có giao dịch.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

**Step 6: Commit**

```bash
git add employees/views.py employees/urls.py employees/forms.py templates/employees/leave_management.html templates/employees/compensatory_credit.html
git commit -m "feat: HR leave management screen and compensatory credit form"
```

---

## Task 8: Cập nhật form giải trình — checkbox dùng giờ bù

**Files:**
- Modify: `explanations/views.py`
- Modify: `templates/explanations/submit.html`

**Step 1: Cập nhật `submit_explanation` trong `explanations/views.py`**

Tìm đoạn xử lý POST trong `submit_explanation`. Thêm đọc giá trị checkbox:

Sau dòng `co_note = request.POST.get('co_note', '').strip()`, thêm:
```python
        ci_use_compensatory = request.POST.get('ci_use_compensatory') == '1'
        co_use_compensatory = request.POST.get('co_use_compensatory') == '1'
```

Sau `exp.ci_note = ci_note` (trong khối `if ci_changed:`), thêm:
```python
            exp.ci_use_compensatory = ci_use_compensatory
```

Sau `exp.co_note = co_note` (trong khối `if co_changed:`), thêm:
```python
            exp.co_use_compensatory = co_use_compensatory
```

Trong hàm `submit_explanation`, thêm vào context của `render`:
```python
    from employees.models import CompensatoryBalance
    try:
        comp_balance = request.user.employee_profile.compensatory_balance
    except Exception:
        comp_balance = None

    # IDs của reasons thuộc nhóm trừ phép
    from explanations.models import ExplanationReason as ER
    leave_reason_ids = list(ER.objects.filter(
        is_active=True
    ).filter(
        name__in=['Nghỉ phép cả ngày', 'Nghỉ phép nửa ngày', 'Đi muộn/ Về sớm',
                  'Nghỉ bù cả ngày', 'Nghỉ bù nửa ngày']
    ).values_list('id', flat=True))
```

Truyền `comp_balance` và `leave_reason_ids` vào context.

**Step 2: Cập nhật `templates/explanations/submit.html`**

Đây là template hiện tại — tìm đoạn input `ci_reason` và thêm checkbox sau phần ghi chú CI:

```html
<!-- Sau phần ci_note textarea, thêm: -->
{% if has_ci and not ci_locked %}
<div id="ci-comp-toggle" class="mb-2" style="display:none">
  <div class="form-check">
    <input class="form-check-input" type="checkbox" name="ci_use_compensatory"
           value="1" id="ci_use_comp"
           {% if exp and exp.ci_use_compensatory %}checked{% endif %}
           {% if not comp_balance or comp_balance.remaining_hours <= 0 %}disabled{% endif %}>
    <label class="form-check-label" for="ci_use_comp">
      Dùng giờ bù thay vì phép
      {% if comp_balance %}
        <small class="text-muted">(còn {{ comp_balance.remaining_hours }}h)</small>
      {% endif %}
    </label>
  </div>
</div>
{% endif %}
```

Tương tự cho CO side với `co_use_compensatory` / `co_use_comp`.

Thêm script vào cuối template để toggle checkbox hiển thị/ẩn theo reason:

```html
<script>
const leaveReasonIds = {{ leave_reason_ids|safe }};
function toggleCompCheckbox(selectId, toggleId) {
  const sel = document.getElementById(selectId);
  const div = document.getElementById(toggleId);
  if (!sel || !div) return;
  sel.addEventListener('change', function() {
    div.style.display = leaveReasonIds.includes(parseInt(this.value)) ? 'block' : 'none';
  });
  div.style.display = leaveReasonIds.includes(parseInt(sel.value)) ? 'block' : 'none';
}
toggleCompCheckbox('id_ci_reason', 'ci-comp-toggle');
toggleCompCheckbox('id_co_reason', 'co-comp-toggle');
</script>
```

**Step 3: Commit**

```bash
git add explanations/views.py templates/explanations/submit.html
git commit -m "feat: add use-compensatory checkbox to explanation submit form"
```

---

## Task 9: Cập nhật TBP review template

**Files:**
- Modify: `templates/explanations/review.html`

**Step 1: Tìm vị trí hiển thị reason trong review.html và thêm thông tin bù**

Trong phần hiển thị CI reason (nếu `exp.ci_use_compensatory`):
```html
{% if exp.ci_use_compensatory %}
  <span class="badge bg-warning text-dark ms-1">Dùng giờ bù</span>
{% endif %}
```

Tương tự cho CO side.

Thêm tóm tắt số dư bù ở đầu form review:
```html
{% if comp_balance %}
<div class="alert alert-info py-2 mb-3">
  <small><i class="bi bi-clock-history"></i>
    Giờ bù còn lại của NV: <strong>{{ comp_balance.remaining_hours }}h</strong>
    (tổng {{ comp_balance.total_hours }}h, đã dùng {{ comp_balance.used_hours }}h)
  </small>
</div>
{% endif %}
```

Cập nhật view `review_explanation` trong `explanations/views.py` để truyền `comp_balance` vào context:
```python
from employees.models import CompensatoryBalance
# trong view:
try:
    comp_balance = exp.employee.compensatory_balance
except CompensatoryBalance.DoesNotExist:
    comp_balance = None
# thêm vào context:
'comp_balance': comp_balance,
```

**Step 2: Commit**

```bash
git add templates/explanations/review.html explanations/views.py
git commit -m "feat: show compensatory info on TBP review screen"
```

---

## Task 10: Cập nhật sidebar + liên kết điều hướng

**Files:**
- Modify: `templates/base/sidebar.html`

**Step 1: Thêm link vào sidebar**

Trong section HR (sau link "Quản lý nhân viên"), thêm:
```html
<a href="/employees/leave-management/"
   class="sidebar-item d-flex align-items-center gap-2 px-2 py-2 rounded text-decoration-none {% if '/employees/leave-management' in request.path %}active{% endif %}"
   data-bs-toggle="tooltip" data-bs-placement="right" title="Phép & Nghỉ bù">
    <i class="bi bi-calendar2-week fs-5"></i>
    <span class="sidebar-label">Phép & Nghỉ bù</span>
</a>
```

Trong section Employee (không phải HR), thêm link cho NV:
```html
{% if user.is_authenticated and not user.is_hr and not user.is_tbp %}
<a href="/employees/my-leave/"
   class="sidebar-item d-flex align-items-center gap-2 px-2 py-2 rounded text-decoration-none {% if '/employees/my-leave' in request.path %}active{% endif %}"
   data-bs-toggle="tooltip" data-bs-placement="right" title="Phép & Nghỉ bù của tôi">
    <i class="bi bi-calendar3 fs-5"></i>
    <span class="sidebar-label">Phép & Nghỉ bù</span>
</a>
{% endif %}
```

**Step 2: Chạy toàn bộ test suite lần cuối**

```bash
make test
```
Expected: tất cả PASS

**Step 3: Commit**

```bash
git add templates/base/sidebar.html
git commit -m "feat: add leave management links to sidebar"
```

---

## Checklist hoàn thành

- [ ] Task 1: ExplanationReason.is_compensatory + seed
- [ ] Task 2: Explanation compensatory flags
- [ ] Task 3: CompensatoryBalance + CompensatoryTransaction models
- [ ] Task 4: compute_record_hours 3-tuple + routing
- [ ] Task 5: calculate_month balance tracking + transactions
- [ ] Task 6: Employee my-leave view
- [ ] Task 7: HR leave management view
- [ ] Task 8: Explanation submit form checkbox
- [ ] Task 9: TBP review template
- [ ] Task 10: Sidebar links

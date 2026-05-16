# Compensatory Leave Management — Design Doc

**Date:** 2026-05-16
**Status:** Approved

---

## Overview

Bổ sung quản lý nghỉ bù (compensatory leave) vào hệ thống HR:
- HR nhập thủ công giờ bù cho nhân viên
- Nhân viên có thể chọn dùng giờ bù thay vì phép khi giải trình
- Màn hình theo dõi phép + bù cho cả NV lẫn HR, có export Excel

---

## 1. Data Models

### `employees/models.py` — 2 model mới

**`CompensatoryBalance`**
Mỗi nhân viên có 1 balance duy nhất (không theo năm, không hết hạn).

| Field | Type | Ghi chú |
|-------|------|---------|
| `employee` | OneToOneField(Employee) | |
| `total_hours` | DecimalField(5,1) | Tổng giờ bù đã được cấp |
| `used_hours` | DecimalField(5,1) | Đã dùng |
| `remaining_hours` | property | `total_hours - used_hours` |

**`CompensatoryTransaction`**
Lịch sử từng giao dịch bù.

| Field | Type | Ghi chú |
|-------|------|---------|
| `employee` | FK(Employee) | |
| `balance` | FK(CompensatoryBalance) | |
| `transaction_type` | choices: `credit` / `debit` | credit = HR cấp, debit = NV dùng |
| `hours` | DecimalField(4,1) | Luôn dương |
| `date` | DateField | |
| `note` | TextField | |
| `created_by` | FK(User, nullable) | |
| `explanation` | OneToOneField(Explanation, nullable) | Link khi debit qua giải trình |
| `created_at` | DateTimeField(auto_now_add) | |

### `explanations/models.py` — thay đổi `Explanation`

Thêm 2 field:
- `ci_use_compensatory = BooleanField(default=False)`
- `co_use_compensatory = BooleanField(default=False)`

Checkbox chỉ hiển thị khi reason thuộc nhóm trừ phép (LEAVE_REASONS, LEAVE_FULL_DAY_REASONS, LEAVE_HALF_DAY_REASONS).

### `explanations/models.py` — thay đổi `ExplanationReason`

Thêm field:
- `is_compensatory = BooleanField(default=False)` — đánh dấu reason tự động dùng giờ bù

Seed thêm 2 lý do mới:
- "Nghỉ bù cả ngày" (`is_compensatory=True`, `requires_full_day_shift=False`)
- "Nghỉ bù nửa ngày" (`is_compensatory=True`, `requires_full_day_shift=True`)

---

## 2. Calculator Logic (`reports/calculator.py`)

### Reason sets mới
```python
COMPENSATORY_FULL_DAY_REASONS = {'Nghỉ bù cả ngày'}
COMPENSATORY_HALF_DAY_REASONS = {'Nghỉ bù nửa ngày'}
```

### `compute_record_hours` — trả về thêm `compensatory_hours`

Signature mới: `-> (work_hours, leave_hours, compensatory_hours)`

Khi result là `LEAVE`, `LEAVE_BLOCK`, hoặc `DAY_OFF`:
- Nếu reason `is_compensatory=True` hoặc `use_compensatory=True` → `d_leave = 0`, `d_compensatory = giờ tương ứng`
- Ngược lại → giữ nguyên logic cũ

### `calculate_month` — kiểm tra số dư & fallback

Trong vòng lặp tính từng record, track **running balance** cho cả phép lẫn bù:

**Fallback khi âm bù:**
- Nếu `running_compensatory - d_compensatory < 0` → bỏ qua `use_compensatory`, xử lý như lý do excused (trừ công, không trừ phép/bù)

**Fallback khi âm phép:**
- Nếu `running_leave - d_leave < 0` → bỏ qua deduction phép, xử lý như excused

Cả 2 fallback đều **âm thầm**, không báo lỗi cho người dùng — đây là tính toán batch cuối tháng.

**Sau khi tính xong:**
- Nếu `compensatory_hours > 0` → tạo `CompensatoryTransaction(debit)` + cập nhật `CompensatoryBalance.used_hours`
- Giữ nguyên flow `LeaveTransaction` hiện tại

---

## 3. UI / Views

### Màn hình NV — "Phép & Nghỉ bù của tôi" (`/employees/my-leave/`)
- Thẻ tóm tắt: Ngày phép (tổng / đã dùng / còn lại) + Giờ bù (tổng / đã dùng / còn lại)
- Bảng lịch sử giao dịch hợp nhất: ngày, loại (phép/bù, cấp/dùng), số lượng, ghi chú, link giải trình
- Filter theo năm (phép) / không filter (bù, cộng dồn vô thời hạn)

### Màn hình HR — "Quản lý phép & nghỉ bù" (`/employees/leave-management/`)
- Bảng danh sách NV: mã, tên, phòng ban, ngày phép còn lại, giờ bù còn lại
- Click vào NV → modal/trang chi tiết lịch sử giao dịch (cả phép lẫn bù)
- Nút **"Cấp giờ bù"**: form nhập số giờ + ngày + ghi chú → tạo `CompensatoryTransaction(credit)` + cập nhật balance
- Filter theo phòng ban
- Export Excel: danh sách NV + số dư phép + số dư bù

### Form giải trình NV (thay đổi `explanations/submit.html`)
- Khi chọn reason nhóm trừ phép → hiện checkbox "Dùng giờ bù thay vì phép"
- Hiển thị inline số giờ bù còn lại
- Nếu giờ bù = 0 → disable checkbox + tooltip "Bạn không còn giờ bù"

### TBP review screen (thay đổi `explanations/review.html`)
- Hiển thị thêm: NV có tick "dùng giờ bù" không + số dư bù hiện tại

---

## 4. Migrations & Seed

- Migration: thêm `CompensatoryBalance`, `CompensatoryTransaction`, 2 field vào `Explanation`, 1 field vào `ExplanationReason`
- Cập nhật management command `seed_error_types` (hoặc tạo `seed_compensatory_reasons`) để seed 2 reason mới

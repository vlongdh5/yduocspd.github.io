# HR Attendance Management System — Design Document

**Date:** 2026-05-08
**Project:** project_hr_2
**Status:** Approved

---

## 1. Mục tiêu

Xây dựng hệ thống web quản lý chấm công nội bộ cho ~100 nhân viên, bao gồm:
- HR upload dữ liệu chấm công từ phần mềm chấm công (file Excel)
- Nhân viên xem chấm công và giải trình ngày công bị lỗi
- TBP (Trưởng bộ phận) phê duyệt giải trình
- HR chạy tính toán ngày công, ngày phép sử dụng và export Excel
- Hệ thống quản lý ngày phép năm còn lại của từng nhân viên

---

## 2. Kiến trúc tổng thể

### Tech Stack

| Thành phần | Lựa chọn |
|---|---|
| Backend + Frontend | Django 5.x (full-stack, một codebase Python duy nhất) |
| UI | Django Templates + Bootstrap 5 (responsive mobile/desktop) |
| Database | SQLite (dev) → PostgreSQL (production) |
| Auth | Django built-in (email + mật khẩu + OTP) |
| OTP | `django-otp` + `pyotp` — Email OTP và Google Authenticator (TOTP) |
| Excel parse/export | `openpyxl` |
| Production server | Gunicorn + Nginx |
| Static files | whitenoise |

### Triển khai

- **Môi trường:** Public internet, HTTPS bắt buộc
- **Truy cập:** Trình duyệt web (Chrome, Safari, Edge) trên máy tính và điện thoại
- **Thiết kế sẵn:** Hỗ trợ gắn Microsoft SSO sau nếu cần

### Cấu trúc project

```
project_hr_2/
├── attendance/        # Upload, records, phát hiện lỗi
├── explanations/      # Giải trình & phê duyệt
├── employees/         # Nhân viên, phòng ban, phép năm
├── accounts/          # Auth (login, OTP, phân quyền)
├── reports/           # Tính công & export Excel
├── config/            # ErrorType, ExplanationReason
├── templates/         # HTML templates Bootstrap 5
├── static/            # CSS, JS, images
├── media/             # File Excel upload
├── manage.py
└── settings.py
```

---

## 3. Phân quyền (Roles)

| Role | Quyền |
|---|---|
| **HR** | Upload file chấm công, chạy tính toán, quản lý nhân viên/phòng ban/phép, export Excel, cấu hình hệ thống |
| **Nhân viên** | Xem chấm công bản thân, nộp/sửa giải trình, xem phép năm |
| **TBP** | Xem + phê duyệt/từ chối giải trình của nhân viên trong phòng mình |

> Một người có thể có nhiều role (TBP vừa là nhân viên vừa là TBP).

---

## 4. Authentication

- **Đăng nhập:** Email + mật khẩu
- **OTP:** Có thể bật/tắt toàn hệ thống (HR Admin cấu hình)
  - Khi bật: nhân viên chọn một trong hai phương thức:
    - **Email OTP:** nhận code qua email mỗi lần đăng nhập
    - **Google Authenticator (TOTP):** setup QR code một lần, dùng app tạo code
  - Khi tắt: chỉ cần email + mật khẩu
- **Tương lai:** Thiết kế sẵn để tích hợp Microsoft SSO (OAuth2/OIDC)

---

## 5. Data Model

### 5.1 Nhân viên & Tổ chức

**Employee**
- `code` — mã nhân viên
- `full_name` — họ tên
- `email` — email đăng nhập
- `department` → FK Department
- `position` — chức vụ
- `start_date` — ngày vào làm
- `is_active` — trạng thái

**Department**
- `name` — tên phòng ban
- `manager` → FK Employee (TBP phụ trách)

### 5.2 Tài khoản & Xác thực

- Django `User` (built-in): email, mật khẩu hash, role
- OTP tạm thời lưu trong cache với TTL 5 phút
- TOTP secret lưu trong DB (mã hóa)

### 5.3 Dữ liệu chấm công

**AttendanceUpload**
- `file` — file Excel gốc
- `month` — tháng xử lý (YYYY-MM)
- `uploaded_by` → FK User
- `uploaded_at` — thời gian upload
- `status` — `processing` / `done` / `error`

**AttendanceRecord**
- `upload` → FK AttendanceUpload
- `employee` → FK Employee
- `date` — ngày
- `check_in` — giờ vào (nullable)
- `check_out` — giờ ra (nullable)
- `shift_code` — mã ca
- `status` — `ok` / `error`
- `error_types` — list loại lỗi phát hiện (JSON)

### 5.4 Cấu hình lỗi *(config-driven)*

**ErrorType**
- `code` — mã lỗi (VD: `MISSING_IN`, `MISSING_OUT`, `LATE`, `EARLY_LEAVE`, `ABSENT`)
- `name` — tên hiển thị
- `description` — mô tả
- `detection_rule` — điều kiện phát hiện (JSON config)
- `is_active` — bật/tắt

### 5.5 Giải trình

**ExplanationReason**
- `name` — tên lý do (VD: "Quên chấm thẻ", "Công tác ngoài", "Làm việc tại nhà")
- `is_active`

**Explanation**
- `record` → FK AttendanceRecord
- `employee` → FK Employee
- `reason` → FK ExplanationReason
- `note` — ghi chú bổ sung (optional)
- `status` — `pending` / `approved` / `rejected`
- `reviewed_by` → FK User (TBP)
- `reviewed_at`
- `reviewer_note` — ghi chú từ TBP khi từ chối

### 5.6 Phép năm

**LeaveBalance**
- `employee` → FK Employee
- `year` — năm
- `total_days` — tổng phép được cấp
- `used_days` — đã dùng
- `remaining_days` — còn lại (computed)

**LeaveTransaction**
- `employee` → FK Employee
- `date` — ngày trừ phép
- `days` — số ngày
- `month` — liên kết tháng tính công
- `note`

### 5.7 Kết quả tính công

**AttendanceCalculation**
- `employee` → FK Employee
- `month` — YYYY-MM
- `actual_workdays` — ngày công thực tế
- `leave_days_used` — ngày phép sử dụng
- `status` — `draft` / `finalized`
- `calculated_at`
- `calculated_by` → FK User

---

## 6. Luồng nghiệp vụ

### Luồng 1: HR upload chấm công
1. HR upload file Excel, chọn tháng
2. Hệ thống parse từng dòng (mã NV, ngày, giờ in/out, mã ca)
3. Đối chiếu với danh sách nhân viên
4. Tự động phát hiện lỗi theo ErrorType config
5. Lưu vào DB, đánh dấu từng ngày: `ok` / `error`
6. HR thấy báo cáo tổng quan: số NV có lỗi, số ngày lỗi

### Luồng 2: Nhân viên giải trình
1. Nhân viên đăng nhập, xem bảng chấm công tháng
2. Ngày lỗi highlight đỏ, ngày chờ duyệt highlight vàng
3. Click vào ngày lỗi → chọn lý do + ghi chú (optional) → Nộp
4. Có thể sửa giải trình nếu TBP chưa duyệt

### Luồng 3: TBP phê duyệt
1. TBP đăng nhập, thấy danh sách giải trình pending của phòng
2. Xem chi tiết: ngày, loại lỗi, lý do nhân viên đưa ra
3. Duyệt hoặc Từ chối + ghi chú lý do
4. Nhân viên thấy kết quả trên hệ thống

### Luồng 4: HR tính công & export
1. HR chọn tháng → chạy tính toán
2. Hệ thống tổng hợp ngày công, xử lý các giải trình đã duyệt
3. Tự động cập nhật LeaveBalance
4. Preview kết quả trên web
5. Export file Excel (theo mẫu — sẽ xác định khi implementation)
6. Lưu lịch sử, có thể re-run nếu cần

> **Lưu ý:** Logic chi tiết tính công (quy tắc chuyển đổi lỗi → ngày công / ngày phép) sẽ được làm rõ khi có file mẫu Excel output.

---

## 7. Giao diện

### Màu trạng thái
- Xanh lá: OK
- Đỏ: Lỗi chưa giải trình
- Vàng: Chờ duyệt
- Xanh dương: Đã duyệt
- Xám: Từ chối

### Nhân viên
- **Trang chủ:** Bảng chấm công tháng (card trên mobile, table trên desktop)
- **Giải trình:** Form chọn lý do + ghi chú
- **Lịch sử giải trình:** Danh sách + trạng thái
- **Phép năm:** Tổng / đã dùng / còn lại

### TBP (thêm vào so với nhân viên)
- **Duyệt giải trình:** Danh sách pending của phòng, filter theo người/ngày

### HR
- **Upload:** Form upload Excel, chọn tháng
- **Tổng quan:** Thống kê sau upload
- **Theo dõi giải trình:** Tỉ lệ toàn công ty
- **Tính công:** Chọn tháng → preview → export
- **Quản lý nhân viên:** CRUD, phân phòng ban, cấp phép
- **Cấu hình:** Quản lý ErrorType, ExplanationReason, bật/tắt OTP

### Backlog (làm sau)
- Tổng quan phòng: bảng chấm công toàn phòng theo tháng (cho TBP)

---

## 8. Thư viện

```
Django>=5.0
django-otp
pyotp
qrcode[pil]       # tạo QR cho Google Authenticator
openpyxl
whitenoise
gunicorn
psycopg2-binary   # PostgreSQL adapter
```

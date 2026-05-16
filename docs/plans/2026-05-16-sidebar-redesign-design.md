# Sidebar Redesign Design

**Date:** 2026-05-16  
**Status:** Approved

## Mục tiêu

Chuyển điều hướng từ Bootstrap navbar ngang (top) sang sidebar dọc bên trái, thu gọn được thành icon-only, để dễ mở rộng tính năng trong tương lai.

## Layout tổng thể

```
<body>
  ├── #sidebar (position: fixed, left 0, full height)
  │     ├── .sidebar-header  (logo + nút toggle)
  │     ├── .sidebar-nav     (menu items theo role)
  │     └── .sidebar-footer  (email user + logout)
  └── #main-content (margin-left: sidebar-width, transition khi toggle)
        ├── .messages-area
        └── {% block content %}
```

**Kích thước:**
- Mở rộng: 240px
- Thu gọn: 64px (icon only)
- Transition: 0.25s ease

**Toggle state** lưu trong `localStorage`.

## Nội dung sidebar (theo role)

- Chấm công — tất cả roles
- Giải trình của tôi — Employee
- Duyệt giải trình — TBP
- *(section HR)*: Upload chấm công, Tính công, Quản lý nhân viên — HR
- *(section Hệ thống)*: Cấu hình — Superuser
- Footer: email, Cài Google Authenticator, Đăng xuất

**Active state:** highlight dựa trên `request.path`.  
**Tooltip:** hiện khi sidebar thu gọn (Bootstrap tooltip).  
**Section labels:** ẩn khi thu gọn.

## Màu sắc

- Sidebar: nền `#1e293b`, text `#cbd5e1`
- Active item: nền `#334155`, text `#ffffff`
- Nội dung: nền trắng / Bootstrap default

## Mobile

- Sidebar ẩn hoàn toàn (width: 0)
- Nút hamburger ở góc trên trái main content
- Mở ra dạng overlay với dimmed background
- Nhấn overlay thì đóng

## File thay đổi

| File | Hành động |
|---|---|
| `templates/base/base.html` | Sửa — thay `<nav>` bằng layout sidebar + include |
| `templates/base/sidebar.html` | Tạo mới — partial chứa sidebar HTML |

Không sửa views, models, hay các template con.

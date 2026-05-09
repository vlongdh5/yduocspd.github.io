# Docker Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Đóng gói ứng dụng HR Attendance thành Docker image, chạy được bằng `docker compose up` với đầy đủ migrate, seed, static files, sẵn sàng deploy.

**Architecture:** Django + Gunicorn bên trong một container, PostgreSQL là container riêng. WhiteNoise serve static files (không cần Nginx riêng). Entrypoint tự động chạy migrate → collectstatic → seed (idempotent) → gunicorn khi container khởi động.

**Tech Stack:** Docker 24+, docker compose v2, Python 3.11-slim, PostgreSQL 16, Gunicorn, WhiteNoise

---

## Tổng quan các file sẽ tạo/sửa

| File | Hành động |
|------|-----------|
| `Dockerfile` | Tạo mới |
| `docker-compose.yml` | Tạo mới |
| `.dockerignore` | Tạo mới |
| `entrypoint.sh` | Tạo mới |
| `hrms/settings/docker.py` | Tạo mới — extends production, tắt SSL redirect |
| `accounts/management/commands/seed_superuser.py` | Tạo mới — tạo admin từ env var |
| `.env.docker.example` | Tạo mới — env mẫu cho docker |
| `Makefile` | Thêm docker targets |

---

### Task 1: Settings cho Docker (`hrms/settings/docker.py`)

Production settings bật `SECURE_SSL_REDIRECT = True` sẽ gây redirect loop khi chạy trong Docker (không có TLS terminator). Cần một settings module riêng cho Docker.

**Files:**
- Tạo: `hrms/settings/docker.py`

**Step 1: Tạo file**

```python
# hrms/settings/docker.py
from .production import *

# Khi chạy sau reverse-proxy (hoặc thử nghiệm trực tiếp), tắt SSL redirect.
# Proxy thật sự (Nginx/Caddy) sẽ xử lý HTTPS bên ngoài.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# Nếu sau proxy forward header X-Forwarded-Proto, bật lại dòng này:
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

**Step 2: Kiểm tra import không lỗi**

```bash
DJANGO_SETTINGS_MODULE=hrms.settings.docker python manage.py check --deploy 2>&1 | head -20
```

Expected: warnings về HTTPS (OK, sẽ fix khi có proxy thật), không có lỗi critical.

**Step 3: Commit**

```bash
git add hrms/settings/docker.py
git commit -m "feat: docker settings — disable SSL redirect for container deploy"
```

---

### Task 2: Seed superuser từ env (`accounts/management/commands/seed_superuser.py`)

Cần tạo admin account lần đầu mà không cần interactive prompt. Dùng env vars `SUPERUSER_EMAIL` + `SUPERUSER_PASSWORD`.

**Files:**
- Tạo: `accounts/management/commands/seed_superuser.py`

**Step 1: Tạo command**

```python
# accounts/management/commands/seed_superuser.py
import os
from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create superuser from SUPERUSER_EMAIL / SUPERUSER_PASSWORD env vars (idempotent)'

    def handle(self, *args, **options):
        email = os.environ.get('SUPERUSER_EMAIL')
        password = os.environ.get('SUPERUSER_PASSWORD')

        if not email or not password:
            self.stdout.write('SUPERUSER_EMAIL / SUPERUSER_PASSWORD not set — skipping.')
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(f'Superuser {email} already exists — skipping.')
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Superuser created: {email}'))
```

**Step 2: Test thủ công**

```bash
SUPERUSER_EMAIL=admin@test.com SUPERUSER_PASSWORD=admin123 \
  python manage.py seed_superuser
# Expected: "Superuser created: admin@test.com"

SUPERUSER_EMAIL=admin@test.com SUPERUSER_PASSWORD=admin123 \
  python manage.py seed_superuser
# Expected: "already exists — skipping." (idempotent)
```

**Step 3: Commit**

```bash
git add accounts/management/commands/seed_superuser.py
git commit -m "feat: seed_superuser command from env vars (idempotent)"
```

---

### Task 3: `entrypoint.sh`

Script chạy khi container khởi động: migrate → collectstatic → seed → gunicorn.

**Files:**
- Tạo: `entrypoint.sh`

**Step 1: Tạo file**

```bash
#!/bin/sh
set -e

echo "==> Migrate"
python manage.py migrate --noinput

echo "==> Collect static"
python manage.py collectstatic --noinput

echo "==> Seed data"
python manage.py seed_error_types
python manage.py seed_explanation_reasons
python manage.py seed_shifts

# Seed departments/employees nếu có file Excel trong image
if [ -f "sample_input/department.xlsx" ]; then
    python manage.py seed_departments
    python manage.py seed_employees
fi

# Tạo superuser từ env (idempotent — bỏ qua nếu đã tồn tại)
python manage.py seed_superuser

echo "==> Start Gunicorn"
exec gunicorn hrms.wsgi:application -c gunicorn.conf.py
```

**Step 2: Cấp quyền execute**

```bash
chmod +x entrypoint.sh
```

**Step 3: Kiểm tra syntax**

```bash
sh -n entrypoint.sh
# Expected: không có output (không lỗi)
```

**Step 4: Commit**

```bash
git add entrypoint.sh
git commit -m "feat: entrypoint.sh — migrate, seed, gunicorn"
```

---

### Task 4: `.dockerignore`

Giữ image nhỏ gọn, không copy file thừa.

**Files:**
- Tạo: `.dockerignore`

**Step 1: Tạo file**

```
.venv/
__pycache__/
*.pyc
*.pyo
.git/
.gitignore
db.sqlite3
media/
staticfiles/
*.env
.env*
!.env.docker.example
docs/
pytest.ini
*.md
!CLAUDE.md
```

**Step 2: Commit**

```bash
git add .dockerignore
git commit -m "chore: add .dockerignore"
```

---

### Task 5: `Dockerfile`

Multi-stage không cần thiết với Django — dùng single stage Python slim.

**Files:**
- Tạo: `Dockerfile`

**Step 1: Tạo file**

```dockerfile
FROM python:3.11-slim

# Không tạo .pyc, output không buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=hrms.settings.docker

WORKDIR /app

# Deps hệ thống cần cho psycopg2-binary và openpyxl
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Cài Python deps trước (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
```

**Step 2: Build thử (chưa cần DB)**

```bash
docker build -t hrms:test .
# Expected: Successfully built ... (không có lỗi)
```

**Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat: Dockerfile — Python 3.11-slim, gunicorn, entrypoint"
```

---

### Task 6: `.env.docker.example` và `docker-compose.yml`

**Files:**
- Tạo: `.env.docker.example`
- Tạo: `docker-compose.yml`

**Step 1: Tạo `.env.docker.example`**

```env
# Copy file này thành .env.docker và điền giá trị thật

SECRET_KEY=change-me-to-a-long-random-string

# PostgreSQL
DB_NAME=hrms
DB_USER=hrms
DB_PASSWORD=hrms_password
DB_HOST=db
DB_PORT=5432

# Email (dùng Gmail App Password hoặc SMTP server của công ty)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@company.com

# Admin đầu tiên (tạo tự động khi container start)
SUPERUSER_EMAIL=admin@company.com
SUPERUSER_PASSWORD=change-me-strong-password

# Domain (dùng khi có reverse proxy thật)
ALLOWED_HOSTS=localhost,127.0.0.1
```

**Step 2: Tạo `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    env_file: .env.docker
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 10

  web:
    build: .
    restart: unless-stopped
    env_file: .env.docker
    environment:
      DB_HOST: db
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - media_files:/app/media

volumes:
  postgres_data:
  media_files:
```

**Step 3: Commit**

```bash
git add .env.docker.example docker-compose.yml
git commit -m "feat: docker-compose with postgres + healthcheck"
```

---

### Task 7: Cập nhật `Makefile`

Thêm các target tiện dụng cho Docker.

**Files:**
- Sửa: `Makefile`

**Step 1: Thêm vào cuối Makefile**

```makefile
# ── Docker ───────────────────────────────────────────────────────────────────
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f web

docker-shell:
	docker compose exec web python manage.py shell

docker-createsuperuser:
	docker compose exec web python manage.py createsuperuser

docker-reset:
	docker compose down -v
	docker compose up -d
```

**Step 2: Commit**

```bash
git add Makefile
git commit -m "chore: add docker targets to Makefile"
```

---

### Task 8: End-to-end smoke test

Xác nhận toàn bộ stack hoạt động.

**Step 1: Chuẩn bị env**

```bash
cp .env.docker.example .env.docker
# Mở .env.docker, điền SECRET_KEY, SUPERUSER_EMAIL, SUPERUSER_PASSWORD
# (các giá trị DB giữ nguyên mặc định đủ để test local)
```

**Step 2: Build và start**

```bash
docker compose build
docker compose up -d
```

**Step 3: Theo dõi log khởi động**

```bash
docker compose logs -f web
```

Expected sequence trong log:
```
==> Migrate
Operations to perform: ...
Running migrations: ...
==> Collect static
...
==> Seed data
Seeded error types: ...
==> Start Gunicorn
[...] Listening at: http://0.0.0.0:8000
```

**Step 4: Kiểm tra HTTP**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/accounts/login/
# Expected: 200
```

**Step 5: Mở browser**

Vào `http://localhost:8000/admin/` → đăng nhập bằng `SUPERUSER_EMAIL` + `SUPERUSER_PASSWORD`.

**Step 6: Kiểm tra trang chính**

Đăng nhập → kiểm tra các section: Upload chấm công, Tính công, Quản lý nhân viên, Cấu hình.

**Step 7: Stop**

```bash
docker compose down
```

---

## Lưu ý khi deploy thật (VPS/server)

1. **ALLOWED_HOSTS** — điền đúng domain/IP, không để `*`
2. **SECRET_KEY** — sinh random: `python -c "import secrets; print(secrets.token_urlsafe(50))"`
3. **Nếu có Nginx/Caddy phía trước**: bỏ comment `SECURE_PROXY_SSL_HEADER` trong `docker.py`, bật lại `SESSION_COOKIE_SECURE = True` và `CSRF_COOKIE_SECURE = True`
4. **Backup PostgreSQL**: volume `postgres_data` cần backup định kỳ
5. **Media files**: volume `media_files` chứa file upload Excel — cần backup

## Thứ tự seed thủ công (nếu cần reset)

```bash
make docker-reset          # xóa volumes, start lại từ đầu
# hoặc seed thủ công:
docker compose exec web python manage.py seed_error_types
docker compose exec web python manage.py seed_explanation_reasons
docker compose exec web python manage.py seed_shifts
docker compose exec web python manage.py seed_departments
docker compose exec web python manage.py seed_employees
docker compose exec web python manage.py seed_superuser
```

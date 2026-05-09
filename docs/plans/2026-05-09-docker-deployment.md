# Docker Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Đóng gói ứng dụng HR Attendance thành Docker image, public ra internet qua Nginx (HTTPS), sẵn sàng deploy một lệnh `docker compose up`.

**Architecture:** 3 container: `db` (PostgreSQL 16) + `web` (Django + Gunicorn) + `nginx` (reverse proxy + TLS). Nginx nhận traffic từ internet (80/443), proxy sang `web:8000`. WhiteNoise serve static files bên trong Django (không cần shared volume). Entrypoint tự động chạy migrate → collectstatic → seed → gunicorn khi `web` khởi động.

**Tech Stack:** Docker 24+, docker compose v2, Python 3.11-slim, PostgreSQL 16, Nginx 1.26-alpine, Gunicorn, WhiteNoise

---

## Tổng quan các file sẽ tạo/sửa

| File | Hành động |
|------|-----------|
| `hrms/settings/docker.py` | Tạo — extends production, bật proxy header |
| `accounts/management/commands/seed_superuser.py` | Tạo — admin từ env var, idempotent |
| `entrypoint.sh` | Tạo — migrate → seed → gunicorn |
| `.dockerignore` | Tạo |
| `Dockerfile` | Tạo |
| `nginx/hrms.conf` | Tạo — Nginx site config (HTTP→HTTPS + proxy) |
| `nginx/ssl/` | Thư mục — đặt cert.pem + key.pem vào đây |
| `docker-compose.yml` | Tạo — db + web + nginx |
| `.env.docker.example` | Tạo — env mẫu |
| `Makefile` | Sửa — thêm docker targets |

---

### Task 1: Settings cho Docker (`hrms/settings/docker.py`)

Django chạy sau Nginx — cần bật `SECURE_PROXY_SSL_HEADER` để nhận đúng scheme từ proxy, đồng thời **không** tự redirect HTTPS (Nginx đã làm việc đó).

**Files:**
- Tạo: `hrms/settings/docker.py`

**Step 1: Tạo file**

```python
# hrms/settings/docker.py
from .production import *

# Django nhận request qua Nginx proxy — đọc X-Forwarded-Proto để biết scheme thật
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Không redirect HTTPS tại Django — Nginx đã xử lý
SECURE_SSL_REDIRECT = False

# HSTS vẫn bật — Nginx forward đúng scheme nên cookie secure hoạt động
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

**Step 2: Kiểm tra import**

```bash
DJANGO_SETTINGS_MODULE=hrms.settings.docker python manage.py check 2>&1 | tail -5
# Expected: System check identified no issues (0 silenced).
```

**Step 3: Commit**

```bash
git add hrms/settings/docker.py
git commit -m "feat: docker settings — proxy SSL header, no self-redirect"
```

---

### Task 2: `seed_superuser` command

Tạo admin lần đầu không cần interactive prompt.

**Files:**
- Tạo: `accounts/management/commands/seed_superuser.py`

**Step 1: Tạo command**

```python
# accounts/management/commands/seed_superuser.py
import os
from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Create superuser from env vars SUPERUSER_EMAIL / SUPERUSER_PASSWORD (idempotent)'

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

**Step 2: Test idempotency thủ công**

```bash
SUPERUSER_EMAIL=admin@test.com SUPERUSER_PASSWORD=Admin123 \
  python manage.py seed_superuser
# Expected: Superuser created: admin@test.com

SUPERUSER_EMAIL=admin@test.com SUPERUSER_PASSWORD=Admin123 \
  python manage.py seed_superuser
# Expected: Superuser admin@test.com already exists — skipping.
```

**Step 3: Commit**

```bash
git add accounts/management/commands/seed_superuser.py
git commit -m "feat: seed_superuser command from env vars (idempotent)"
```

---

### Task 3: `entrypoint.sh`

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

echo "==> Seed data (idempotent)"
python manage.py seed_error_types
python manage.py seed_explanation_reasons
python manage.py seed_shifts

if [ -f "sample_input/department.xlsx" ]; then
    python manage.py seed_departments
    python manage.py seed_employees
fi

python manage.py seed_superuser

echo "==> Start Gunicorn"
exec gunicorn hrms.wsgi:application -c gunicorn.conf.py
```

**Step 2: Kiểm tra syntax**

```bash
chmod +x entrypoint.sh
sh -n entrypoint.sh
# Expected: không output (không lỗi syntax)
```

**Step 3: Commit**

```bash
git add entrypoint.sh
git commit -m "feat: entrypoint.sh — migrate, seed, gunicorn"
```

---

### Task 4: `.dockerignore`

**Files:**
- Tạo: `.dockerignore`

**Step 1: Tạo file**

```
.venv/
__pycache__/
*.pyc
.git/
db.sqlite3
media/
staticfiles/
.env
.env.*
!.env.docker.example
docs/
pytest.ini
nginx/ssl/
```

**Step 2: Commit**

```bash
git add .dockerignore
git commit -m "chore: .dockerignore"
```

---

### Task 5: `Dockerfile`

**Files:**
- Tạo: `Dockerfile`

**Step 1: Tạo file**

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=hrms.settings.docker

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
```

**Step 2: Build thử (kiểm tra không lỗi, DB chưa cần)**

```bash
docker build -t hrms:test .
# Expected: Successfully built ...
```

**Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat: Dockerfile — Python 3.11-slim"
```

---

### Task 6: Nginx config (`nginx/hrms.conf`)

Nginx làm 3 việc: redirect HTTP→HTTPS, terminate TLS, proxy sang Django.

**Files:**
- Tạo: `nginx/hrms.conf`
- Tạo: `nginx/ssl/.gitkeep` (thư mục giữ chỗ cho cert)

**Step 1: Tạo `nginx/hrms.conf`**

```nginx
# nginx/hrms.conf

# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS — proxy đến Django
server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Upload file Excel có thể lớn
    client_max_body_size 20M;

    location / {
        proxy_pass         http://web:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

**Step 2: Tạo thư mục ssl**

```bash
mkdir -p nginx/ssl
touch nginx/ssl/.gitkeep
```

> **Thêm cert:** Đặt `cert.pem` và `key.pem` vào `nginx/ssl/` trước khi `docker compose up`.
>
> Nếu chưa có cert, sinh self-signed để test:
> ```bash
> openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
>   -keyout nginx/ssl/key.pem \
>   -out nginx/ssl/cert.pem \
>   -subj "/CN=localhost"
> ```

**Step 3: Thêm `nginx/ssl/` vào `.gitignore`** (không commit cert)

```bash
echo "nginx/ssl/*.pem" >> .gitignore
echo "nginx/ssl/*.crt" >> .gitignore
echo "nginx/ssl/*.key" >> .gitignore
```

**Step 4: Commit**

```bash
git add nginx/ .gitignore
git commit -m "feat: nginx config — HTTP→HTTPS redirect, proxy to Django"
```

---

### Task 7: `docker-compose.yml` và `.env.docker.example`

**Files:**
- Tạo: `docker-compose.yml`
- Tạo: `.env.docker.example`

**Step 1: Tạo `.env.docker.example`**

```env
# Copy thành .env.docker và điền giá trị thật

# Django
SECRET_KEY=change-me-to-a-50-char-random-string
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# PostgreSQL
DB_NAME=hrms
DB_USER=hrms
DB_PASSWORD=strong_db_password_here
DB_HOST=db
DB_PORT=5432

# Email (Gmail App Password hoặc SMTP công ty)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@company.com

# Admin đầu tiên (tạo tự động khi web container start lần đầu)
SUPERUSER_EMAIL=admin@company.com
SUPERUSER_PASSWORD=StrongAdminPassword123!
```

**Step 2: Tạo `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
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
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - media_files:/app/media
    expose:
      - "8000"   # chỉ expose nội bộ, Nginx mới ra ngoài

  nginx:
    image: nginx:1.26-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/hrms.conf:/etc/nginx/conf.d/hrms.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - web

volumes:
  postgres_data:
  media_files:
```

> **Lưu ý:** `web` chỉ `expose` (không `ports`) — không thể truy cập trực tiếp từ internet, chỉ qua Nginx.

**Step 3: Commit**

```bash
git add docker-compose.yml .env.docker.example
git commit -m "feat: docker-compose — db + web + nginx (HTTPS)"
```

---

### Task 8: Cập nhật `Makefile`

**Files:**
- Sửa: `Makefile`

**Step 1: Thêm docker targets**

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

docker-logs-nginx:
	docker compose logs -f nginx

docker-shell:
	docker compose exec web python manage.py shell

docker-reset:
	docker compose down -v && docker compose up -d

docker-cert-selfsigned:
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
	  -keyout nginx/ssl/key.pem \
	  -out nginx/ssl/cert.pem \
	  -subj "/CN=localhost"
```

**Step 2: Commit**

```bash
git add Makefile
git commit -m "chore: docker + cert targets in Makefile"
```

---

### Task 9: End-to-end smoke test

**Step 1: Chuẩn bị env và cert**

```bash
cp .env.docker.example .env.docker
# Điền SECRET_KEY (bắt buộc), giữ nguyên DB_* để test local

# Sinh self-signed cert cho test
make docker-cert-selfsigned
```

**Step 2: Build và start**

```bash
docker compose build
docker compose up -d
docker compose logs -f web   # chờ thấy "Listening at: http://0.0.0.0:8000"
```

**Step 3: Test HTTP redirect**

```bash
curl -I http://localhost/
# Expected: HTTP/1.1 301 Moved Permanently  +  Location: https://localhost/
```

**Step 4: Test HTTPS (bỏ qua verify vì self-signed)**

```bash
curl -k -o /dev/null -w "%{http_code}" https://localhost/accounts/login/
# Expected: 200
```

**Step 5: Kiểm tra X-Forwarded-Proto**

```bash
curl -k -s https://localhost/accounts/login/ | grep -i "csrf"
# Expected: có csrfmiddlewaretoken trong form (Django render được, không bị 403)
```

**Step 6: Mở browser**

Vào `https://localhost/` (chấp nhận self-signed warning) → đăng nhập bằng `SUPERUSER_EMAIL` + `SUPERUSER_PASSWORD`.

**Step 7: Stop**

```bash
docker compose down
```

---

## Deploy lên server thật (VPS/cloud)

### Chuẩn bị cert Let's Encrypt (cách đơn giản nhất)

```bash
# Trên server, cài certbot
apt install certbot

# Lấy cert (phải trỏ domain về IP server trước)
certbot certonly --standalone -d yourdomain.com

# Copy cert vào project
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   nginx/ssl/key.pem
```

### Cập nhật `.env.docker`

```bash
ALLOWED_HOSTS=yourdomain.com
SECRET_KEY=<50-char-random>   # python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### Cập nhật `nginx/hrms.conf`

Đổi `server_name _;` thành tên domain thật:
```nginx
server_name yourdomain.com www.yourdomain.com;
```

### Start

```bash
docker compose up -d
```

### Gia hạn cert tự động (cron)

```bash
# Thêm vào crontab của server
0 3 * * 1 certbot renew --quiet && \
  cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /path/to/project/nginx/ssl/cert.pem && \
  cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   /path/to/project/nginx/ssl/key.pem && \
  docker compose -f /path/to/project/docker-compose.yml exec nginx nginx -s reload
```

---

## Thứ tự seed thủ công (nếu cần reset)

```bash
make docker-reset   # xóa volumes, restart từ đầu (entrypoint seed lại tự động)

# Hoặc seed từng cái:
docker compose exec web python manage.py seed_error_types
docker compose exec web python manage.py seed_explanation_reasons
docker compose exec web python manage.py seed_shifts
docker compose exec web python manage.py seed_departments
docker compose exec web python manage.py seed_employees
docker compose exec web python manage.py seed_superuser
```

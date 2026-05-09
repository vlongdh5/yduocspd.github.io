from .production import *

# Django chạy sau Nginx — đọc X-Forwarded-Proto để biết scheme thật
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Không self-redirect HTTPS — Nginx đã xử lý
SECURE_SSL_REDIRECT = False

# Cookie secure vẫn bật (Nginx forward đúng scheme)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

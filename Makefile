.PHONY: dev test migrate seed createsuperuser collectstatic \
        docker-build docker-up docker-down docker-logs docker-logs-nginx \
        docker-shell docker-reset docker-cert-selfsigned

dev:
	DJANGO_SETTINGS_MODULE=hrms.settings.development .venv/bin/python manage.py runserver

test:
	.venv/bin/pytest -v

migrate:
	.venv/bin/python manage.py migrate

seed:
	.venv/bin/python manage.py seed_error_types
	.venv/bin/python manage.py seed_departments
	.venv/bin/python manage.py seed_shifts
	.venv/bin/python manage.py seed_employees
	.venv/bin/python manage.py seed_explanation_reasons

createsuperuser:
	.venv/bin/python manage.py createsuperuser

collectstatic:
	.venv/bin/python manage.py collectstatic --noinput

prod:
	DJANGO_SETTINGS_MODULE=hrms.settings.production .venv/bin/gunicorn hrms.wsgi:application -c gunicorn.conf.py

# ── Docker ────────────────────────────────────────────────────────────────────
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

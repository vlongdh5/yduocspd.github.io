.PHONY: dev test migrate seed createsuperuser collectstatic prod \
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
	$(DC) build web
	$(DC) up -d --no-deps web

# ── Docker ────────────────────────────────────────────────────────────────────
DC = docker compose --env-file .env.docker

docker-build:
	$(DC) build

docker-up:
	$(DC) up -d

docker-down:
	$(DC) down

docker-logs:
	$(DC) logs -f web

docker-logs-nginx:
	$(DC) logs -f nginx

docker-shell:
	$(DC) exec web python manage.py shell

docker-reset:
	$(DC) down -v && $(DC) up -d

docker-cert-selfsigned:
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
	  -keyout nginx/ssl/key.pem \
	  -out nginx/ssl/cert.pem \
	  -subj "/CN=localhost"

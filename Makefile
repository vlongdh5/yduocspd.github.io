.PHONY: dev test migrate seed createsuperuser collectstatic

dev:
	DJANGO_SETTINGS_MODULE=hrms.settings.development .venv/bin/python manage.py runserver

test:
	.venv/bin/pytest -v

migrate:
	.venv/bin/python manage.py migrate

seed:
	.venv/bin/python manage.py seed_error_types

createsuperuser:
	.venv/bin/python manage.py createsuperuser

collectstatic:
	.venv/bin/python manage.py collectstatic --noinput

prod:
	DJANGO_SETTINGS_MODULE=hrms.settings.production .venv/bin/gunicorn hrms.wsgi:application -c gunicorn.conf.py

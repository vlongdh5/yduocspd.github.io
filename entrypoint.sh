#!/bin/sh
set -e

echo "==> Migrate"
python manage.py migrate --noinput

echo "==> Create cache table"
python manage.py createcachetable

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

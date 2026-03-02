#!/bin/sh

echo "Waiting for database"
python manage.py wait_for_db
python manage.py createcachetable

echo "Collecting static files"
python manage.py collectstatic --noinput --clear

echo "Generating OpenAPI schema"
python manage.py spectacular --color --file schema.yml

echo "Checking SKABEN integrity"
python manage.py check_integrity

if [ ${ENVIRONMENT} != 'dev' ]; then
    echo "Apply database migrations"
    python manage.py migrate
    echo "Run production server"
    gunicorn -b 0.0.0.0:8000 server.wsgi
else
    echo "Run dev server"
    python manage.py runserver 0.0.0.0:8000
fi

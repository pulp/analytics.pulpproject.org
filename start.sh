#!/bin/sh

set -eu

if [ -n "${PULP_DEPLOYMENT:-}" ]
then
  ./manage check --deploy --fail-level WARNING
fi

./manage.py migrate

gunicorn -b "0.0.0.0:8080" app.wsgi

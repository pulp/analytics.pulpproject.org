#!/bin/sh

./manage.py migrate
./manage.py createsuperuser --no-input

./manage.py runserver 0.0.0.0:8080

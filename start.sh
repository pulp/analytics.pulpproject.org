#!/bin/sh

./manage.py makemigrations pulpanalytics

./manage.py runserver 0.0.0.0:8080

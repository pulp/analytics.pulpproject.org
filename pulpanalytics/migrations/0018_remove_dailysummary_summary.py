# Generated by Django 4.1.7 on 2023-04-17 07:41

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("pulpanalytics", "0017_numbercount_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dailysummary",
            name="summary",
        ),
    ]
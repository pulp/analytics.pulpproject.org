# Generated by Django 4.1.7 on 2023-04-08 21:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pulpanalytics", "0012_deploymentstats"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="postgresversioncount",
            index=models.Index(fields=["summary"], name="pulpanalyti_summary_3ad8a0_idx"),
        ),
    ]
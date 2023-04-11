# Generated by Django 4.1.7 on 2023-04-11 11:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pulpanalytics", "0014_xyzversioncount_xyversioncount_and_more"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="component",
            unique_together={("system", "name")},
        ),
        migrations.AddIndex(
            model_name="component",
            index=models.Index(fields=["name"], name="pulpanalyti_name_459b73_idx"),
        ),
    ]
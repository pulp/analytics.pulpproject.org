# Generated by Django 4.1.7 on 2023-04-05 13:15

import django.db.models.deletion
from django.db import migrations, models


def move_postgresql_version_data_up(apps, schema_editor):
    DailySummary = apps.get_model("pulpanalytics", "DailySummary")
    for ds in DailySummary.objects.all():
        for item in ds.summary.postgresql_version:
            ds.postgresversioncount_set.create(version=item.version, count=item.count)
        ds.summary.ClearField("postgresql_version")
        ds.save()


def move_postgresql_version_data_down(apps, schema_editor):
    DailySummary = apps.get_model("pulpanalytics", "DailySummary")
    for ds in DailySummary.objects.all():
        for item in ds.postgresversioncount_set.all():
            ds.summary.postgresql_version.add(version=item.version, count=item.count)
        ds.save()
        ds.postgresversioncount_set.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pulpanalytics", "0010_remove_dailysummary_id_alter_dailysummary_date"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostgresVersionCount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("version", models.PositiveIntegerField()),
                ("count", models.PositiveIntegerField()),
                (
                    "summary",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="pulpanalytics.dailysummary"
                    ),
                ),
            ],
            options={
                "unique_together": {("summary", "version")},
            },
        ),
        migrations.RunPython(
            code=move_postgresql_version_data_up,
            reverse_code=move_postgresql_version_data_down,
            elidable=True,
        ),
    ]
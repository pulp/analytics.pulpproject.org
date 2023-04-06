# Generated by Django 4.1.7 on 2023-03-28 09:32

from django.db import migrations, models


def fold_service_counts_into_system_up(apps, schema_editor):
    System = apps.get_model("pulpanalytics", "System")
    OnlineContentApps = apps.get_model("pulpanalytics", "OnlineContentApps")
    OnlineWorkers = apps.get_model("pulpanalytics", "OnlineWorkers")
    content_app_hosts = OnlineContentApps.objects.filter(system=models.OuterRef("pk")).values(
        "hosts"
    )
    content_app_processes = OnlineContentApps.objects.filter(system=models.OuterRef("pk")).values(
        "processes"
    )
    worker_hosts = OnlineWorkers.objects.filter(system=models.OuterRef("pk")).values("hosts")
    worker_processes = OnlineWorkers.objects.filter(system=models.OuterRef("pk")).values(
        "processes"
    )
    System.objects.annotate(
        new_content_app_hosts=models.Subquery(content_app_hosts),
        new_content_app_processes=models.Subquery(content_app_processes),
        new_worker_hosts=models.Subquery(worker_hosts),
        new_worker_processes=models.Subquery(worker_processes),
    ).update(
        content_app_hosts=models.F("new_content_app_hosts"),
        content_app_processes=models.F("new_content_app_processes"),
        worker_hosts=models.F("new_worker_hosts"),
        worker_processes=models.F("new_worker_processes"),
    )


def fold_service_counts_into_system_down(apps, schema_editor):
    System = apps.get_model("pulpanalytics", "System")
    OnlineContentApps = apps.get_model("pulpanalytics", "OnlineContentApps")
    OnlineWorkers = apps.get_model("pulpanalytics", "OnlineWorkers")
    for system in System.objects.all():
        OnlineContentApps.objects.create(
            system=system, hosts=system.content_app_hosts, processes=system.content_app_processes
        )
        OnlineWorkers.objects.create(
            system=system, hosts=system.worker_hosts, processes=system.worker_processes
        )


class Migration(migrations.Migration):
    dependencies = [
        ("pulpanalytics", "0008_DATA_fix_rbac_stats"),
    ]

    operations = [
        migrations.AddField(
            model_name="system",
            name="content_app_hosts",
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name="system",
            name="content_app_processes",
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name="system",
            name="worker_hosts",
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name="system",
            name="worker_processes",
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.RunSQL(
            sql="",
            reverse_sql="SET CONSTRAINTS ALL IMMEDIATE;",
        ),
        migrations.RunPython(
            code=fold_service_counts_into_system_up,
            reverse_code=fold_service_counts_into_system_down,
            elidable=True,
        ),
        migrations.RunSQL(
            sql="SET CONSTRAINTS ALL IMMEDIATE;",
            reverse_sql="",
        ),
        migrations.DeleteModel(
            name="OnlineContentApps",
        ),
        migrations.DeleteModel(
            name="OnlineWorkers",
        ),
    ]

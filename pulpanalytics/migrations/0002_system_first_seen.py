# Generated by Django 4.0.8 on 2022-10-15 10:05

from django.db import migrations, models
import django.utils.timezone


def adjust_first_seen(apps, schema_editor):
    System = apps.get_model('pulpanalytics', 'System')
    sub_q = models.Subquery(
        System.objects.filter(
            system_id=models.OuterRef("system_id")
        ).values("system_id").annotate(
            min__created=models.Min("created")
        ).values("min__created")
    )
    System.objects.annotate(
        min__created=sub_q
    ).update(
        first_seen=models.F("min__created")
    )


class Migration(migrations.Migration):

    dependencies = [
        ('pulpanalytics', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='system',
            name='first_seen',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(
            code=adjust_first_seen,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
    ]
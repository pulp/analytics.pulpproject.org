import json
import sys

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import semver

from django.core.management.base import BaseCommand
from django.db.models import Avg
from google.protobuf.json_format import MessageToJson

from pulpanalytics.summary_pb2 import Summary
from pulpanalytics.models import Component, DailySummary, OnlineContentApps, OnlineWorkers, System


CLEANUP_AFTER_N_DAYS = 14


class Command(BaseCommand):
    help = 'Create data summary and delete old System data.'

    @staticmethod
    def _find_very_first_date_to_summarize():
        if not System.objects.exists():
            sys.exit("There are no DailySummary entries and no System entries to summarize.")

        earliest_system_datetime = System.objects.order_by('created').first().created
        first_summary_date = date(
            year=earliest_system_datetime.year,
            month=earliest_system_datetime.month,
            day=earliest_system_datetime.day
        )

        return first_summary_date

    @classmethod
    def _get_next_date_to_summarize(cls):
        if not DailySummary.objects.exists():
            next_summary_date = cls._find_very_first_date_to_summarize()
        else:
            next_summary_date = DailySummary.objects.order_by('-date').first().date + timedelta(days=1)

        if next_summary_date < date.today():
            return next_summary_date
        else:
            return

    @staticmethod
    def _handle_online_workers(systems, summary):
        online_workers_qs = OnlineWorkers.objects.filter(system__in=systems)
        online_workers_stats = online_workers_qs.aggregate(Avg('processes'), Avg('hosts'))

        summary.online_workers.processes__avg = online_workers_stats['processes__avg']
        summary.online_workers.hosts__avg = online_workers_stats['hosts__avg']

    @staticmethod
    def _handle_online_content_apps(systems, summary):
        online_content_apps_qs = OnlineContentApps.objects.filter(system__in=systems)
        online_content_apps_stats = online_content_apps_qs.aggregate(Avg('processes'), Avg('hosts'))

        summary.online_content_apps.processes__avg = online_content_apps_stats['processes__avg']
        summary.online_content_apps.hosts__avg = online_content_apps_stats['hosts__avg']

    @staticmethod
    def _handle_components(systems, summary):
        components_qs = Component.objects.filter(system__in=systems)
        for name in components_qs.values_list('name', flat=True).distinct():

            xy_dict = defaultdict(int)
            xyz_dict = defaultdict(int)

            for component in components_qs.filter(name=name):
                try:
                    semver_version = semver.parse(component.version)
                except ValueError:  # Pulp uses x.y.z.dev which is not semver compatible
                    component.version = component.version.replace('.dev', '-dev')
                    semver_version = semver.parse(component.version)
                xy_version = f"{semver_version['major']}.{semver_version['minor']}"
                xy_dict[xy_version] += 1
                xyz_dict[component.version] +=1

            for version, count in xy_dict.items():
                xy_component = summary.xy_component.add()
                xy_component.name = name
                xy_component.version = version
                xy_component.count = count

            for version, count in xyz_dict.items():
                xyz_component = summary.xyz_component.add()
                xyz_component.name = name
                xyz_component.version = version
                xyz_component.count = count

    def handle(self, *args, **options):
        while True:
            next_summary_date = self._get_next_date_to_summarize()

            if not next_summary_date:
                break

            summary_start_datetime = datetime(
                year=next_summary_date.year,
                month=next_summary_date.month,
                day=next_summary_date.day,
                tzinfo=timezone.utc
            )
            summary_end_datetime = summary_start_datetime + timedelta(days=1)

            systems = System.objects.filter(created__gte=summary_start_datetime).filter(created__lt=summary_end_datetime)

            if systems.exists():
                summary = Summary()
                self._handle_online_workers(systems, summary)
                self._handle_online_content_apps(systems, summary)
                self._handle_components(systems, summary)

                json_summary = json.loads(MessageToJson(summary))
            else:
                json_summary = {}

            DailySummary.objects.create(date=next_summary_date, summary=json_summary)
            print(f'Wrote summary for {next_summary_date}')

        last_night_midnight = datetime.today().replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        delete_older_than_datetime = last_night_midnight- timedelta(days=CLEANUP_AFTER_N_DAYS)
        num, obj_per_type = System.objects.filter(created__lt=delete_older_than_datetime).delete()

        if num:
            num = obj_per_type["pulpanalytics.System"]

        print(f"Deleted {num} Systems from before {delete_older_than_datetime}.")

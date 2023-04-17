import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg, Count
from django.db.models.functions import TruncDay

from pulpanalytics.models import Component, DailySummary, DeploymentStats, System
from pulpanalytics.summary_pb2 import Summary

CLEANUP_AFTER_N_DAYS = 14


class Command(BaseCommand):
    help = "Create data summary and delete old System data."

    @staticmethod
    def _find_very_first_date_to_summarize():
        if not System.objects.exists():
            sys.exit("There are no DailySummary entries and no System entries to summarize.")

        return System.objects.order_by("created").first().created.date()

    @classmethod
    def _get_next_date_to_summarize(cls):
        if not DailySummary.objects.exists():
            next_summary_date = cls._find_very_first_date_to_summarize()
        else:
            next_summary_date = DailySummary.objects.order_by("-date").first().date + timedelta(
                days=1
            )

        if next_summary_date < date.today():
            return next_summary_date
        else:
            return

    @staticmethod
    def _handle_deployment_stats(systems, daily_summary):
        deployment_stats = systems.aggregate(
            Avg("worker_processes"),
            Avg("worker_hosts"),
            Avg("content_app_processes"),
            Avg("content_app_hosts"),
        )

        DeploymentStats.objects.create(
            summary=daily_summary,
            online_worker_processes_avg=deployment_stats["worker_processes__avg"],
            online_worker_hosts_avg=deployment_stats["worker_hosts__avg"],
            online_content_app_processes_avg=deployment_stats["content_app_processes__avg"],
            online_content_app_hosts_avg=deployment_stats["content_app_hosts__avg"],
        )

    @staticmethod
    def _handle_components(systems, daily_summary):
        components_qs = Component.objects.filter(system__in=systems)
        for name in components_qs.values_list("name", flat=True).distinct():
            xy_dict = defaultdict(int)
            xyz_dict = defaultdict(int)

            for component in components_qs.filter(name=name):
                version_components = component.version.split(".")
                xy_version = f"{version_components[0]}.{version_components[1]}"
                xy_dict[xy_version] += 1
                xyz_dict[component.version] += 1

            for version, count in xy_dict.items():
                daily_summary.xyversioncount_set.create(name=name, version=version, count=count)

            for version, count in xyz_dict.items():
                daily_summary.xyzversioncount_set.create(name=name, version=version, count=count)

    @staticmethod
    def _handle_age(systems, daily_summary):
        age_q = systems.values("age").annotate(count=Count("system_id"))

        for entry in age_q:
            daily_summary.agecount_set.create(age=entry["age"].days, count=entry["count"])

    @staticmethod
    def _handle_postgresql_version(systems, daily_summary):
        postgresql_dict = defaultdict(int)
        for system in systems:
            version = system.postgresql_version
            postgresql_dict[version] += 1
        for version, count in postgresql_dict.items():
            daily_summary.postgresversioncount_set.create(version=version, count=count)

    @staticmethod
    def _handle_rbac_stats(systems, daily_summary):
        NAMES = ["users", "groups", "domains", "custom_access_policies", "custom_roles"]
        counters = {name: defaultdict(int) for name in NAMES}
        for system in systems:
            for name in NAMES:
                count = getattr(system, name)
                if count is not None:
                    counters[name][count] += 1
        for name in NAMES:
            for number, count in counters[name].items():
                daily_summary.numbercount_set.create(name=name, number=number, count=count)

    def handle(self, *args, **options):
        while True:
            next_summary_date = self._get_next_date_to_summarize()

            if not next_summary_date:
                break

            summary_start_datetime = datetime(
                year=next_summary_date.year,
                month=next_summary_date.month,
                day=next_summary_date.day,
                tzinfo=timezone.utc,
            )
            summary_end_datetime = summary_start_datetime + timedelta(days=1)

            systems = (
                System.objects.annotate(age=TruncDay("created") - TruncDay("first_seen"))
                .filter(created__gte=summary_start_datetime)
                .filter(created__lt=summary_end_datetime)
            )
            persistent_systems = systems.filter(
                age__gte=timedelta(days=settings.PERSISTENT_MIN_AGE_DAYS)
            )

            summary = Summary()

            with transaction.atomic():
                daily_summary = DailySummary.objects.create(date=next_summary_date, summary=summary)
                self._handle_age(systems, daily_summary)
                self._handle_components(persistent_systems, daily_summary)
                self._handle_postgresql_version(persistent_systems, daily_summary)
                self._handle_deployment_stats(persistent_systems, daily_summary)
                self._handle_rbac_stats(persistent_systems, daily_summary)
            print(f"Wrote summary for {next_summary_date}")

        last_night_midnight = datetime.today().replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
        delete_older_than_datetime = last_night_midnight - timedelta(days=CLEANUP_AFTER_N_DAYS)
        num, obj_per_type = System.objects.filter(created__lt=delete_older_than_datetime).delete()

        if num:
            num = obj_per_type["pulpanalytics.System"]

        print(f"Deleted {num} Systems from before {delete_older_than_datetime}.")

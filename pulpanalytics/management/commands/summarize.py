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
    def _handle_rbac_stats(systems, summary):
        users_dict = defaultdict(int)
        groups_dict = defaultdict(int)
        domains_dict = defaultdict(int)
        custom_access_policies_dict = defaultdict(int)
        custom_roles_dict = defaultdict(int)
        for system in systems:
            if system.users is not None:
                users_dict[system.users] += 1
            if system.groups is not None:
                groups_dict[system.groups] += 1
            if system.domains is not None:
                domains_dict[system.domains] += 1
            if system.custom_access_policies is not None:
                custom_access_policies_dict[system.custom_access_policies] += 1
            if system.custom_roles is not None:
                custom_roles_dict[system.custom_roles] += 1
        for number in sorted(users_dict.keys()):
            summary.rbac_stats.users.add(number=number, count=users_dict[number])
        for number in sorted(groups_dict.keys()):
            summary.rbac_stats.groups.add(number=number, count=groups_dict[number])
        for number in sorted(domains_dict.keys()):
            summary.rbac_stats.domains.add(number=number, count=domains_dict[number])
        for number in sorted(custom_access_policies_dict.keys()):
            summary.rbac_stats.custom_access_policies.add(
                number=number, count=custom_access_policies_dict[number]
            )
        for number in sorted(custom_roles_dict.keys()):
            summary.rbac_stats.custom_roles.add(number=number, count=custom_roles_dict[number])

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
            if systems.exists():
                self._handle_rbac_stats(persistent_systems, summary)

            with transaction.atomic():
                daily_summary = DailySummary.objects.create(date=next_summary_date, summary=summary)
                self._handle_age(systems, daily_summary)
                self._handle_components(persistent_systems, daily_summary)
                self._handle_postgresql_version(persistent_systems, daily_summary)
                self._handle_deployment_stats(persistent_systems, daily_summary)
            print(f"Wrote summary for {next_summary_date}")

        last_night_midnight = datetime.today().replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
        delete_older_than_datetime = last_night_midnight - timedelta(days=CLEANUP_AFTER_N_DAYS)
        num, obj_per_type = System.objects.filter(created__lt=delete_older_than_datetime).delete()

        if num:
            num = obj_per_type["pulpanalytics.System"]

        print(f"Deleted {num} Systems from before {delete_older_than_datetime}.")

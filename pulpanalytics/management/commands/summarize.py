import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from django.db.models.functions import TruncDay

from pulpanalytics.models import Component, DailySummary, System
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
    def _handle_online_workers(systems, summary):
        online_workers_stats = systems.aggregate(Avg("worker_processes"), Avg("worker_hosts"))

        try:
            summary.online_workers.processes__avg = online_workers_stats["worker_processes__avg"]
            summary.online_workers.hosts__avg = online_workers_stats["worker_hosts__avg"]
        except TypeError:
            pass

    @staticmethod
    def _handle_online_content_apps(systems, summary):
        online_content_apps_stats = systems.aggregate(
            Avg("content_app_processes"), Avg("content_app_hosts")
        )

        try:
            summary.online_content_apps.processes__avg = online_content_apps_stats[
                "content_app_processes__avg"
            ]
            summary.online_content_apps.hosts__avg = online_content_apps_stats[
                "content_app_hosts__avg"
            ]
        except TypeError:
            pass

    @staticmethod
    def _handle_components(systems, summary):
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
                xy_component = summary.xy_component.add()
                xy_component.name = name
                xy_component.version = version
                xy_component.count = count

            for version, count in xyz_dict.items():
                xyz_component = summary.xyz_component.add()
                xyz_component.name = name
                xyz_component.version = version
                xyz_component.count = count

    @staticmethod
    def _handle_age(systems, summary):
        age_q = systems.values("age").annotate(count=Count("system_id"))

        for entry in age_q:
            age_count = summary.age_count.add()
            age_count.age = entry["age"].days
            age_count.count = entry["count"]

    @staticmethod
    def _handle_postgresql_version(systems, summary):
        postgresql_dict = defaultdict(int)
        for system in systems:
            version = system.postgresql_version
            postgresql_dict[version] += 1
        for version, count in postgresql_dict.items():
            new_postgresql_version_entry = summary.postgresql_version.add()
            new_postgresql_version_entry.version = version
            new_postgresql_version_entry.count = count

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
                self._handle_online_workers(persistent_systems, summary)
                self._handle_online_content_apps(persistent_systems, summary)
                self._handle_components(persistent_systems, summary)
                self._handle_age(systems, summary)
                self._handle_postgresql_version(persistent_systems, summary)
                self._handle_rbac_stats(persistent_systems, summary)

            DailySummary.objects.create(date=next_summary_date, summary=summary)
            print(f"Wrote summary for {next_summary_date}")

        last_night_midnight = datetime.today().replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
        delete_older_than_datetime = last_night_midnight - timedelta(days=CLEANUP_AFTER_N_DAYS)
        num, obj_per_type = System.objects.filter(created__lt=delete_older_than_datetime).delete()

        if num:
            num = obj_per_type["pulpanalytics.System"]

        print(f"Deleted {num} Systems from before {delete_older_than_datetime}.")

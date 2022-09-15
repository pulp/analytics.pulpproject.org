from collections import defaultdict
from contextlib import suppress
import logging

from django.db import transaction
from django.http import HttpResponse
from django.template import loader
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from pulpanalytics.models import Component, DailySummary, OnlineContentApps, OnlineWorkers, System
from pulpanalytics.telemetry_pb2 import Telemetry


logger = logging.getLogger(__name__)


class LogAndDropData(BaseException):
    pass


def _check_component_version(version):
    if not version.count('.') == 2:
        raise LogAndDropData(f"The version string {version} does not have two periods.")

    x, y, z = version.split('.')
    for item in [x, y, z]:
        if not item.isdigit():
            raise LogAndDropData(f"The version string {version} does not only contain numbers.")


def _save_components(system, telemetry):
    components = []
    for component in telemetry.components:
        _check_component_version(component.version)
        components.append(
            Component(system=system, name=component.name, version=component.version)
        )
    Component.objects.bulk_create(components)


def _save_online_content_apps(system, telemetry):
    hosts = telemetry.online_content_apps.hosts
    processes = telemetry.online_content_apps.processes
    OnlineContentApps.objects.create(system=system, hosts=hosts, processes=processes)


def _save_online_workers(system, telemetry):
    hosts = telemetry.online_workers.hosts
    processes = telemetry.online_workers.processes
    OnlineWorkers.objects.create(system=system, hosts=hosts, processes=processes)


@method_decorator(csrf_exempt, name='dispatch')
class RootView(View):

    @staticmethod
    def _add_workers_data(context, daily_summary):
        with suppress(KeyError):
            context["online_workers_hosts_avg"].append(
                daily_summary.online_workers_hosts_avg_data_point()
            )

        with suppress(KeyError):
            context["online_workers_processes_avg"].append(
                daily_summary.online_workers_processes_avg_data_point()
            )

    @staticmethod
    def _add_content_apps_data(context, daily_summary):
        with suppress(KeyError):
            context["online_content_apps_hosts_avg"].append(
                daily_summary.online_content_apps_hosts_avg_data_point()
            )

        with suppress(KeyError):
            context["online_content_apps_processes_avg"].append(
                daily_summary.online_content_apps_processes_avg_data_point()
            )

    @staticmethod
    def _label_xy_versions_data_for_plugin(context, data_key):
        new_data = []
        for version, data in context[data_key].items():
            new_data.append(
                {
                    "label": version,
                    "data": data,
                }
            )
        context[data_key] = new_data

    @classmethod
    def _label_xy_versions_data(cls, context):
        cls._label_xy_versions_data_for_plugin(context, "ansible_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "certguard_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "container_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "cookbook_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "core_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "deb_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "file_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "galaxy_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "gem_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "maven_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "ostree_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "python_xy_versions")
        cls._label_xy_versions_data_for_plugin(context, "rpm_xy_versions")

    @staticmethod
    def _add_xy_version_for_plugin(context, daily_summary, plugin_name, data_key):
        with suppress(KeyError):
            xy_components = daily_summary.summary["xyComponent"]

            for item in filter(lambda x: x["name"] == plugin_name, xy_components):
                context[data_key][item["version"]].append(
                    {
                        "x": daily_summary.epoch_ms_timestamp(),
                        "y": item["count"],
                    }
                )

    @classmethod
    def _add_xy_versions_data(cls, context, daily_summary):
        cls._add_xy_version_for_plugin(context, daily_summary, "ansible", "ansible_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "certguard", "certguard_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "container", "container_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "cookbook", "cookbook_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "core", "core_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "deb", "deb_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "file", "file_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "galaxy", "galaxy_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "gem", "gem_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "maven", "maven_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "ostree", "ostree_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "python", "python_xy_versions")
        cls._add_xy_version_for_plugin(context, daily_summary, "rpm", "rpm_xy_versions")

    def get(self, request):
        # import pydevd_pycharm
        # pydevd_pycharm.settrace('localhost', port=39017, stdoutToServer=True, stderrToServer=True, suspend=False)
        template = loader.get_template('pulpanalytics/index.html')
        context = {
            "online_workers_hosts_avg": [],
            "online_workers_processes_avg": [],
            "online_content_apps_hosts_avg": [],
            "online_content_apps_processes_avg": [],
            "ansible_xy_versions": defaultdict(list),  # ansible
            "certguard_xy_versions": defaultdict(list),  # certguard
            "container_xy_versions": defaultdict(list),  # container
            "cookbook_xy_versions": defaultdict(list),  # cookbook
            "core_xy_versions": defaultdict(list),  # core
            "deb_xy_versions": defaultdict(list),  # deb
            "file_xy_versions": defaultdict(list),  # file
            "galaxy_xy_versions": defaultdict(list),  # galaxy
            "gem_xy_versions": defaultdict(list),  # gem
            "maven_xy_versions": defaultdict(list),  # maven
            "ostree_xy_versions": defaultdict(list),  # ostree
            "python_xy_versions": defaultdict(list),  # python
            "rpm_xy_versions": defaultdict(list),  # rpm
        }
        for daily_summary in DailySummary.objects.order_by('date'):
            self._add_workers_data(context, daily_summary)
            self._add_content_apps_data(context, daily_summary)
            self._add_xy_versions_data(context, daily_summary)

        self._label_xy_versions_data(context)

        return HttpResponse(template.render(context, request))

    def post(self, request):
        telemetry = Telemetry()
        telemetry.ParseFromString(request.body)

        try:
            with transaction.atomic():
                system = System.objects.create(system_id=telemetry.system_id)
                _save_components(system, telemetry)
                _save_online_content_apps(system, telemetry)
                _save_online_workers(system, telemetry)
        except LogAndDropData as exc:
            logger.error(f"Dropping data due a validation error: {exc.args[0]}\n{telemetry}")

        return HttpResponse()

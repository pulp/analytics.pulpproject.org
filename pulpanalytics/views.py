import logging
from collections import defaultdict
from contextlib import suppress
from functools import lru_cache
from itertools import accumulate

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.template import loader
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from git import Repo

from pulpanalytics.models import Component, DailySummary, OnlineContentApps, OnlineWorkers, System
from pulpanalytics.telemetry_pb2 import Telemetry

logger = logging.getLogger(__name__)


PLUGINS = [
    "ansible",
    "certguard",
    "container",
    "cookbook",
    "core",
    "deb",
    "file",
    "galaxy",
    "gem",
    "maven",
    "ostree",
    "python",
    "rpm",
]


class LogAndDropData(IntegrityError):
    def __init__(self, msg):
        logger.error(msg)
        super().__init__(msg)


@lru_cache(maxsize=1)
def _get_git_revision():
    return Repo().commit().hexsha


def _check_component_version(version):
    if not version.count(".") == 2:
        raise LogAndDropData(f"The version string {version} does not have two periods.")

    x, y, z = version.split(".")
    for item in [x, y, z]:
        if not item.isdigit():
            raise LogAndDropData(f"The version string {version} does not only contain numbers.")


def _save_components(system, telemetry):
    components = []
    for component in telemetry.components:
        if not settings.COLLECT_DEV_SYSTEMS:
            _check_component_version(component.version)
        components.append(Component(system=system, name=component.name, version=component.version))
    Component.objects.bulk_create(components)


def _save_online_content_apps(system, telemetry):
    hosts = telemetry.online_content_apps.hosts
    processes = telemetry.online_content_apps.processes
    OnlineContentApps.objects.create(system=system, hosts=hosts, processes=processes)


def _save_online_workers(system, telemetry):
    hosts = telemetry.online_workers.hosts
    processes = telemetry.online_workers.processes
    OnlineWorkers.objects.create(system=system, hosts=hosts, processes=processes)


def _label_data_for_key(context, data_key, fill=False):
    new_data = []
    for version, data in context[data_key].items():
        new_data.append(
            {
                "label": version,
                "data": data,
            }
        )
        if fill:
            new_data[-1]["fill"] = "-1"
    if fill and new_data:
        new_data[0]["fill"] = True
    context[data_key] = new_data


def _add_xy_versions_data(context, daily_summary):
    xy_components = daily_summary.summary.xy_component
    for item in xy_components:
        if item.name in PLUGINS:
            context[f"{item.name}_xy_versions"][item.version].append(
                {
                    "x": daily_summary.epoch_ms_timestamp(),
                    "y": item.count,
                }
            )


def _add_demography(context, daily_summary):
    def _accumulator(prev, value):
        return value | {"count": prev["count"] + value["count"]}

    context["demography"] = []
    if daily_summary is None:
        return
    raw_data = sorted(daily_summary.summary.age_count, key=lambda i: i.age, reverse=True)
    if not raw_data:
        # No data available
        return
    age = raw_data[0].age + 1
    data = []
    # Fill the gaps and transform to dicts
    for item in raw_data:
        while age > item.age:
            data.append({"age": age, "count": 0})
            age -= 1
        data.append({"age": item.age, "count": item.count})
        age -= 1

    context["demography"].append(
        {
            "label": "count",
            "data": data,
            "parsing": {
                "xAxisKey": "age",
                "yAxisKey": "count",
            },
        }
    )
    context["demography"].append(
        {
            "label": "accumulated",
            "data": list(accumulate(data, _accumulator)),
            "parsing": {
                "xAxisKey": "age",
                "yAxisKey": "count",
            },
            "fill": True,
        }
    )


def _add_age_data(context, daily_summary):
    timestamp = daily_summary.epoch_ms_timestamp()
    bucket = [0, 0, 0]
    for item in daily_summary.summary.age_count:
        if item.age <= 1:
            bucket[0] += item.count
        elif item.age <= 7:
            bucket[1] += item.count
        else:
            bucket[2] += item.count
    context["age_count"][">=8"].append({"x": timestamp, "y": bucket[2]})
    context["age_count"]["2-7"].append({"x": timestamp, "y": bucket[1]})
    context["age_count"]["0-1"].append({"x": timestamp, "y": bucket[0]})


def _add_workers_data(context, daily_summary):
    context["online_workers_hosts_avg"].append(daily_summary.online_workers_hosts_avg_data_point())

    context["online_workers_processes_avg"].append(
        daily_summary.online_workers_processes_avg_data_point()
    )


def _add_content_apps_data(context, daily_summary):
    context["online_content_apps_hosts_avg"].append(
        daily_summary.online_content_apps_hosts_avg_data_point()
    )

    context["online_content_apps_processes_avg"].append(
        daily_summary.online_content_apps_processes_avg_data_point()
    )


@method_decorator(csrf_exempt, name="dispatch")
class RootView(View):
    def get(self, request):
        template = loader.get_template("pulpanalytics/index.html")
        context = {
            "PLUGINS": PLUGINS,
            "online_workers_hosts_avg": [],
            "online_workers_processes_avg": [],
            "online_content_apps_hosts_avg": [],
            "online_content_apps_processes_avg": [],
            "age_count": defaultdict(list),
        }
        context.update({f"{plugin}_xy_versions": defaultdict(list) for plugin in PLUGINS})
        _add_demography(context, DailySummary.objects.order_by("date").last())

        for daily_summary in DailySummary.objects.order_by("date"):
            _add_age_data(context, daily_summary)
            _add_workers_data(context, daily_summary)
            _add_content_apps_data(context, daily_summary)
            _add_xy_versions_data(context, daily_summary)

        context["plugin_xy_versions"] = {}
        for plugin in PLUGINS:
            _label_data_for_key(context, f"{plugin}_xy_versions")
            context["plugin_xy_versions"][plugin] = context.pop(f"{plugin}_xy_versions")
        _label_data_for_key(context, "age_count", fill=True)

        context["revision"] = _get_git_revision()

        return HttpResponse(template.render(context, request))

    def post(self, request):
        telemetry = Telemetry()
        telemetry.ParseFromString(request.body)

        with suppress(IntegrityError), transaction.atomic():
            system = System.objects.create(system_id=telemetry.system_id)
            _save_components(system, telemetry)
            _save_online_content_apps(system, telemetry)
            _save_online_workers(system, telemetry)

        return HttpResponse()

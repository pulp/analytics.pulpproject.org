import logging
from collections import defaultdict
from contextlib import suppress
from functools import lru_cache
from itertools import accumulate

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.template import loader
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from git import Repo
from packaging.version import parse as parse_version

from pulpanalytics.analytics_pb2 import Analytics
from pulpanalytics.models import Component, DailySummary, System

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


def _save_components(system, analytics):
    components = []
    for component in analytics.components:
        if not settings.COLLECT_DEV_SYSTEMS:
            _check_component_version(component.version)
        components.append(Component(system=system, name=component.name, version=component.version))
    Component.objects.bulk_create(components)


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
    if daily_summary.summary.age_count:
        timestamp = daily_summary.epoch_ms_timestamp()
        bucket = [0, 0, 0, 0]
        for item in daily_summary.summary.age_count:
            if item.age <= 0:
                bucket[0] += item.count
            elif item.age <= 2:
                bucket[1] += item.count
            elif item.age <= 7:
                bucket[2] += item.count
            else:
                bucket[3] += item.count
        context["age_count"][">=8"].append({"x": timestamp, "y": bucket[3]})
        context["age_count"]["3-7"].append({"x": timestamp, "y": bucket[2]})
        context["age_count"]["1-2"].append({"x": timestamp, "y": bucket[1]})
        context["age_count"]["0"].append({"x": timestamp, "y": bucket[0]})


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


@require_GET
def postgresql_versions_view(request):
    date = request.GET.get("date")
    qs = DailySummary.objects.order_by("date")
    if date is not None:
        qs = qs.filter(date__lte=date)
    daily_summary = qs.prefetch_related("postgresversioncount_set").last()
    if daily_summary is None:
        return JsonResponse({})
    data = daily_summary.postgresversioncount_set.order_by("version")
    labels = [item.pretty_version for item in data]
    datasets = [{"data": [item.count for item in data]}]
    return JsonResponse({"labels": labels, "datasets": datasets})


@require_GET
def plugin_stats_view(request, plugin):
    if plugin in PLUGINS:
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        z_stream = request.GET.get("z_stream")
        labels = []
        counts = defaultdict(list)
        qs = DailySummary.objects.order_by("date")
        if start_date is not None:
            qs = qs.filter(date__gte=start_date)
        if end_date is not None:
            qs = qs.filter(date__lte=end_date)
        for index, daily_summary in enumerate(qs):
            if z_stream:
                plugin_stats = daily_summary.summary.xyz_component
            else:
                plugin_stats = daily_summary.summary.xy_component
            labels.append(daily_summary.date)
            for item in plugin_stats:
                if item.name != plugin:
                    continue
                dataset = counts[item.version]
                while len(dataset) <= index:
                    dataset.append(0)
                dataset[index] += item.count
        for dataset in counts.values():
            while len(dataset) <= index:
                dataset.append(0)
        datasets = [
            {"label": key, "data": counts[key], "fill": "-1"}
            for key in sorted(counts.keys(), key=parse_version, reverse=True)
        ]
        if datasets:
            datasets[0]["fill"] = "origin"
        return JsonResponse({"labels": labels, "datasets": datasets})
    raise Http404("Not found")


@require_GET
def rbac_stats_view(request, measure):
    if measure in ["users", "groups", "domains", "custom_access_policies", "custom_roles"]:
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        bucket = request.GET.get("bucket")
        labels = []
        counts = defaultdict(list)
        qs = DailySummary.objects.order_by("date")
        if start_date is not None:
            qs = qs.filter(date__gte=start_date)
        if end_date is not None:
            qs = qs.filter(date__lte=end_date)
        for index, daily_summary in enumerate(qs):
            rbac_stats = daily_summary.summary.rbac_stats
            labels.append(daily_summary.date)
            for item in getattr(rbac_stats, measure):
                if bucket and item.number:
                    number = 1 << (item.number - 1).bit_length()
                else:
                    number = item.number
                dataset = counts[number]
                while len(dataset) <= index:
                    dataset.append(0)
                dataset[index] += item.count
        for dataset in counts.values():
            while len(dataset) <= index:
                dataset.append(0)
        datasets = [
            {"label": str(key), "data": counts[key], "fill": "-1"} for key in sorted(counts.keys())
        ]
        if bucket:
            last_label = 0
            for dataset in datasets:
                label = int(dataset["label"])
                if last_label < label:
                    dataset["label"] = f"{last_label}-{label}"
                last_label = label + 1

        if datasets:
            datasets[0]["fill"] = "origin"
        return JsonResponse({"labels": labels, "datasets": datasets})
    raise Http404("Not found")


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
            "postgresql_versions_count": [],
            "postgresql_versions_labels": [],
        }
        _add_demography(context, DailySummary.objects.order_by("date").last())

        for daily_summary in DailySummary.objects.order_by("date"):
            _add_age_data(context, daily_summary)
            _add_workers_data(context, daily_summary)
            _add_content_apps_data(context, daily_summary)

        _label_data_for_key(context, "age_count", fill=True)

        context["deployment"] = settings.PULP_DEPLOYMENT
        context["revision"] = _get_git_revision()

        return HttpResponse(template.render(context, request))

    def post(self, request):
        analytics = Analytics()
        analytics.ParseFromString(request.body)

        kwargs = {}
        if analytics.HasField("rbac_stats"):
            kwargs["users"] = analytics.rbac_stats.users
            kwargs["groups"] = analytics.rbac_stats.groups
            kwargs["domains"] = analytics.rbac_stats.domains
            kwargs["custom_access_policies"] = analytics.rbac_stats.custom_access_policies
            kwargs["custom_roles"] = analytics.rbac_stats.custom_roles
        with suppress(IntegrityError), transaction.atomic():
            system = System.objects.create(
                system_id=analytics.system_id,
                postgresql_version=analytics.postgresql_version,
                content_app_processes=analytics.online_content_apps.processes,
                content_app_hosts=analytics.online_content_apps.hosts,
                worker_processes=analytics.online_workers.processes,
                worker_hosts=analytics.online_workers.hosts,
                **kwargs,
            )
            _save_components(system, analytics)

        return HttpResponse()

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
from pulpanalytics.models import (
    AgeCount,
    Component,
    DailySummary,
    DeploymentStats,
    System,
    XYVersionCount,
    XYZVersionCount,
)

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
def deployment_stats_view(request, component):
    if component not in ["worker", "content_app"]:
        raise Http404("Not found")

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    qs = DeploymentStats.objects.order_by("summary_id")
    if start_date is not None:
        qs = qs.filter(summary_id__gte=start_date)
    if end_date is not None:
        qs = qs.filter(summary_id__lte=end_date)
    labels = list(qs.values_list("summary_id", flat=True))
    datasets = [
        {
            "label": "Mean Processes",
            "data": list(qs.values_list(f"online_{component}_processes_avg", flat=True)),
        },
        {
            "label": "Mean Hosts",
            "data": list(qs.values_list(f"online_{component}_hosts_avg", flat=True)),
        },
    ]
    return JsonResponse({"labels": labels, "datasets": datasets})


@require_GET
def plugin_stats_view(request, plugin):
    if plugin not in PLUGINS:
        raise Http404("Not found")

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    z_stream = request.GET.get("z_stream")
    labels = []
    counts_lists = defaultdict(list)
    version_count_class = XYZVersionCount if z_stream else XYVersionCount
    qs = version_count_class.objects.filter(name=plugin).order_by("summary_id")
    if start_date is not None:
        qs = qs.filter(summary__gte=start_date)
    if end_date is not None:
        qs = qs.filter(summary__lte=end_date)
    index = -1
    date = None
    for item in qs:
        if item.summary_id != date:
            index += 1
            date = item.summary_id
            labels.append(date)
        counts_list = counts_lists[item.version]
        while len(counts_list) <= index:
            counts_list.append(0)
        counts_list[index] += item.count
    for counts_list in counts_lists.values():
        while len(counts_list) <= index:
            counts_list.append(0)
    datasets = [
        {"label": key, "data": counts_lists[key], "fill": "-1"}
        for key in sorted(counts_lists.keys(), key=parse_version, reverse=True)
    ]
    if datasets:
        datasets[0]["fill"] = "origin"
    return JsonResponse({"labels": labels, "datasets": datasets})


@require_GET
def demography_view(request):
    def _accumulator(prev, value):
        return value | {"count": prev["count"] + value["count"]}

    date = request.GET.get("date")
    ds_qs = DailySummary.objects.order_by("date")
    if date is not None:
        ds_qs = ds_qs.filter(date__lte=date)
    daily_summary = ds_qs.last()
    if daily_summary is None:
        return JsonResponse({})
    qs = daily_summary.agecount_set.order_by("-age")
    if not qs:
        # No data available
        return JsonResponse({})
    age = qs[0].age + 1
    data = []
    # Fill the gaps and transform to dicts
    for item in qs:
        while age > item.age:
            data.append({"age": age, "count": 0})
            age -= 1
        data.append({"age": item.age, "count": item.count})
        age -= 1

    datasets = [
        {
            "label": "count",
            "data": data,
            "parsing": {
                "xAxisKey": "age",
                "yAxisKey": "count",
            },
        },
        {
            "label": "accumulated",
            "data": list(accumulate(data, _accumulator)),
            "parsing": {
                "xAxisKey": "age",
                "yAxisKey": "count",
            },
            "fill": True,
        },
    ]
    return JsonResponse({"datasets": datasets})


@require_GET
def systems_by_age_view(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    bucket = request.GET.get("bucket")
    labels = []
    counts_lists = defaultdict(list)
    qs = AgeCount.objects.order_by("summary_id")
    if start_date is not None:
        qs = qs.filter(summary__gte=start_date)
    if end_date is not None:
        qs = qs.filter(summary__lte=end_date)
    index = -1
    date = None
    for item in qs:
        if item.summary_id != date:
            index += 1
            date = item.summary_id
            labels.append(date)
        if bucket and item.age:
            age = 1 << (item.age - 1).bit_length()
        else:
            age = item.age
        counts_list = counts_lists[age]
        while len(counts_list) <= index:
            counts_list.append(0)
        counts_list[index] += item.count
    for counts_list in counts_lists.values():
        while len(counts_list) <= index:
            counts_list.append(0)
    datasets = [
        {"label": str(key), "data": counts_lists[key], "fill": "-1"}
        for key in sorted(counts_lists.keys())
    ]
    if bucket:
        last_label = 0
        for dataset in datasets:
            label = int(dataset["label"])
            if last_label < label:
                dataset["label"] = f"{last_label}-{label}"
            last_label = label + 1

    datasets.reverse()
    if datasets:
        datasets[0]["fill"] = "origin"
    return JsonResponse({"labels": labels, "datasets": datasets})


@require_GET
def rbac_stats_view(request, measure):
    if measure not in ["users", "groups", "domains", "custom_access_policies", "custom_roles"]:
        raise Http404("Not found")
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


@method_decorator(csrf_exempt, name="dispatch")
class RootView(View):
    def get(self, request):
        template = loader.get_template("pulpanalytics/index.html")
        context = {
            "PLUGINS": PLUGINS,
            "deployment": settings.PULP_DEPLOYMENT,
            "revision": _get_git_revision(),
        }
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

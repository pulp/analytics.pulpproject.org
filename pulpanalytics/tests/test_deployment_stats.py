import pytest
from django.urls import reverse
from django.utils import timezone

from pulpanalytics.models import DailySummary, DeploymentStats
from pulpanalytics.summary_pb2 import Summary


@pytest.fixture(params=["worker", "content_app"])
def component(request):
    return request.param


def test_deployment_stats_empty(db, client, component):
    response = client.get(
        reverse("pulpanalytics:deployment_stats", kwargs={"component": component})
    )

    assert response.status_code == 200
    assert response.json() == {
        "labels": [],
        "datasets": [
            {"label": "Mean Processes", "data": []},
            {"label": "Mean Hosts", "data": []},
        ],
    }


def test_deployment_stats_no_data(db, client, component):
    date = timezone.now().date()
    summary = Summary()
    DailySummary.objects.create(date=date, summary=summary)

    response = client.get(
        reverse("pulpanalytics:deployment_stats", kwargs={"component": component})
    )

    assert response.status_code == 200
    assert response.json() == {
        "labels": [],
        "datasets": [
            {"label": "Mean Processes", "data": []},
            {"label": "Mean Hosts", "data": []},
        ],
    }


def test_deployment_stats_none_data(db, client, component):
    date = timezone.now().date()
    summary = Summary()
    daily_summary = DailySummary.objects.create(date=date, summary=summary)
    DeploymentStats.objects.create(summary=daily_summary)

    response = client.get(
        reverse("pulpanalytics:deployment_stats", kwargs={"component": component})
    )

    assert response.status_code == 200
    assert response.json() == {
        "labels": [str(date)],
        "datasets": [
            {"label": "Mean Processes", "data": [None]},
            {"label": "Mean Hosts", "data": [None]},
        ],
    }


def test_deployment_stats_data(db, client, component):
    date = timezone.now().date()
    summary = Summary()
    daily_summary = DailySummary.objects.create(date=date, summary=summary)
    DeploymentStats.objects.create(
        summary=daily_summary,
        online_worker_processes_avg=1.5,
        online_worker_hosts_avg=2.0,
        online_content_app_processes_avg=2.5,
        online_content_app_hosts_avg=3.0,
    )

    response = client.get(
        reverse("pulpanalytics:deployment_stats", kwargs={"component": component})
    )

    offset = 0 if component == "worker" else 1

    assert response.status_code == 200
    assert response.json() == {
        "labels": [str(date)],
        "datasets": [
            {"label": "Mean Processes", "data": [1.5 + offset]},
            {"label": "Mean Hosts", "data": [2.0 + offset]},
        ],
    }

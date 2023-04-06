import pytest
from django.urls import reverse
from django.utils import timezone

from pulpanalytics.models import DailySummary
from pulpanalytics.summary_pb2 import Summary


@pytest.fixture(params=["users", "groups", "domains", "custom_access_policies", "custom_roles"])
def measure(request):
    return request.param


def test_empty_summary(db, client, measure):
    response = client.get(reverse("pulpanalytics:rbac_stats", kwargs={"measure": measure}))

    assert response.status_code == 200
    assert response.json() == {"labels": [], "datasets": []}


def test_no_data(db, client, measure):
    date = timezone.now().date()
    summary = Summary()
    DailySummary.objects.create(date=date, summary=summary)

    response = client.get(reverse("pulpanalytics:rbac_stats", kwargs={"measure": measure}))

    assert response.status_code == 200
    assert response.json() == {"labels": [str(date)], "datasets": []}


def test_data(db, client, measure):
    date = timezone.now().date()
    summary = Summary()
    stats = getattr(summary.rbac_stats, measure)
    stats.add(number=4, count=6)
    stats.add(number=5, count=4)
    stats.add(number=0, count=6)
    stats.add(number=3, count=7)
    DailySummary.objects.create(date=date, summary=summary)

    response = client.get(reverse("pulpanalytics:rbac_stats", kwargs={"measure": measure}))

    assert response.status_code == 200
    assert response.json() == {
        "labels": [str(date)],
        "datasets": [
            {"data": [6], "fill": "origin", "label": "0"},
            {"data": [7], "fill": "-1", "label": "3"},
            {"data": [6], "fill": "-1", "label": "4"},
            {"data": [4], "fill": "-1", "label": "5"},
        ],
    }


def test_data_bucket(db, client, measure):
    date = timezone.now().date()
    summary = Summary()
    stats = getattr(summary.rbac_stats, measure)
    stats.add(number=4, count=6)
    stats.add(number=17, count=4)
    stats.add(number=0, count=6)
    stats.add(number=3, count=7)
    stats.add(number=1, count=8)
    stats.add(number=2, count=9)
    DailySummary.objects.create(date=date, summary=summary)

    response = client.get(
        reverse("pulpanalytics:rbac_stats", kwargs={"measure": measure}) + "?bucket=1"
    )

    assert response.status_code == 200
    assert response.json() == {
        "labels": [str(date)],
        "datasets": [
            {"data": [6], "fill": "origin", "label": "0"},
            {"data": [8], "fill": "-1", "label": "1"},
            {"data": [9], "fill": "-1", "label": "2"},
            {"data": [13], "fill": "-1", "label": "3-4"},
            {"data": [4], "fill": "-1", "label": "5-32"},
        ],
    }

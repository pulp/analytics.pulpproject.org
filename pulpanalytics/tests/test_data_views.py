from django.urls import reverse
from django.utils import timezone

from pulpanalytics.models import DailySummary
from pulpanalytics.summary_pb2 import Summary


def test_pg_version_empty(db, client):
    response = client.get(reverse("pulpanalytics:postgresql_versions"))

    assert response.status_code == 200
    assert response.json() == {}


def test_pg_version_no_data(db, client):
    date = timezone.now().date()
    summary = Summary()
    DailySummary.objects.create(date=date, summary=summary)

    response = client.get(reverse("pulpanalytics:postgresql_versions"))

    assert response.status_code == 200
    assert response.json() == {"labels": [], "datasets": [{"data": []}]}


def test_pg_version_data(db, client):
    date = timezone.now().date()
    summary = Summary()
    daily_summary = DailySummary.objects.create(date=date, summary=summary)
    daily_summary.postgresversioncount_set.create(version=90105, count=1)
    daily_summary.postgresversioncount_set.create(version=0, count=2)
    daily_summary.postgresversioncount_set.create(version=100001, count=3)
    daily_summary.postgresversioncount_set.create(version=110000, count=4)
    daily_summary.postgresversioncount_set.create(version=140005, count=5)
    daily_summary.postgresversioncount_set.create(version=90200, count=6)

    response = client.get(reverse("pulpanalytics:postgresql_versions"))

    assert response.status_code == 200
    assert response.json() == {
        "labels": ["Unknown", "9.1.5", "9.2.0", "10.1", "11.0", "14.5"],
        "datasets": [
            {"data": [2, 1, 6, 3, 4, 5]},
        ],
    }

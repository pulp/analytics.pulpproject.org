from django.urls import reverse
from django.utils import timezone

from pulpanalytics.models import DailySummary
from pulpanalytics.summary_pb2 import Summary


def test_systems_by_age_empty(db, client):
    response = client.get(reverse("pulpanalytics:systems_by_age"))

    assert response.status_code == 200
    assert response.json() == {"labels": [], "datasets": []}


def test_systems_by_age_no_data(db, client):
    date = timezone.now().date()
    summary = Summary()
    DailySummary.objects.create(date=date, summary=summary)

    response = client.get(reverse("pulpanalytics:systems_by_age"))

    assert response.status_code == 200
    assert response.json() == {"labels": [], "datasets": []}


def test_systems_by_age_data(db, client):
    date = timezone.now().date()
    summary = Summary()
    daily_summary = DailySummary.objects.create(date=date, summary=summary)
    daily_summary.agecount_set.create(age=2, count=1)
    daily_summary.agecount_set.create(age=1, count=2)
    daily_summary.agecount_set.create(age=3, count=3)
    daily_summary.agecount_set.create(age=5, count=4)
    daily_summary.agecount_set.create(age=6, count=5)

    response = client.get(reverse("pulpanalytics:systems_by_age"))

    assert response.status_code == 200
    assert response.json() == {
        "labels": [str(date)],
        "datasets": [
            {"data": [5], "fill": "origin", "label": "6"},
            {"data": [4], "fill": "-1", "label": "5"},
            {"data": [3], "fill": "-1", "label": "3"},
            {"data": [1], "fill": "-1", "label": "2"},
            {"data": [2], "fill": "-1", "label": "1"},
        ],
    }

    response = client.get(reverse("pulpanalytics:systems_by_age") + "?bucket=1")

    assert response.status_code == 200
    assert response.json() == {
        "labels": [str(date)],
        "datasets": [
            {"data": [9], "fill": "origin", "label": "5-8"},
            {"data": [3], "fill": "-1", "label": "3-4"},
            {"data": [1], "fill": "-1", "label": "2"},
            {"data": [2], "fill": "-1", "label": "0-1"},
        ],
    }


def test_demography_empty(db, client):
    response = client.get(reverse("pulpanalytics:demography"))

    assert response.status_code == 200
    assert response.json() == {}


def test_demography_no_data(db, client):
    date = timezone.now().date()
    summary = Summary()
    DailySummary.objects.create(date=date, summary=summary)

    response = client.get(reverse("pulpanalytics:demography"))

    assert response.status_code == 200
    assert response.json() == {}


def test_demography_data(db, client):
    date = timezone.now().date()
    summary = Summary()
    daily_summary = DailySummary.objects.create(date=date, summary=summary)
    daily_summary.agecount_set.create(age=2, count=1)
    daily_summary.agecount_set.create(age=1, count=2)
    daily_summary.agecount_set.create(age=3, count=3)
    daily_summary.agecount_set.create(age=5, count=4)
    daily_summary.agecount_set.create(age=6, count=5)

    response = client.get(reverse("pulpanalytics:demography"))

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"datasets"}
    assert data["datasets"] == [
        {
            "label": "count",
            "data": [
                {"age": 7, "count": 0},
                {"age": 6, "count": 5},
                {"age": 5, "count": 4},
                {"age": 4, "count": 0},
                {"age": 3, "count": 3},
                {"age": 2, "count": 1},
                {"age": 1, "count": 2},
            ],
            "parsing": {"xAxisKey": "age", "yAxisKey": "count"},
        },
        {
            "data": [
                {"age": 7, "count": 0},
                {"age": 6, "count": 5},
                {"age": 5, "count": 9},
                {"age": 4, "count": 9},
                {"age": 3, "count": 12},
                {"age": 2, "count": 13},
                {"age": 1, "count": 15},
            ],
            "fill": True,
            "label": "accumulated",
            "parsing": {"xAxisKey": "age", "yAxisKey": "count"},
        },
    ]


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

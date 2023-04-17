import pytest
from django.urls import reverse
from django.utils import timezone

from pulpanalytics.models import DailySummary
from pulpanalytics.views import PLUGINS


@pytest.mark.parametrize("plugin", PLUGINS[0:2])
def test_empty_summary(db, client, plugin):
    response = client.get(reverse("pulpanalytics:plugin_stats", kwargs={"plugin": plugin}))

    assert response.status_code == 200
    assert response.json() == {"labels": [], "datasets": []}


@pytest.mark.parametrize("plugin", PLUGINS[0:2])
def test_no_data(db, client, plugin):
    date = timezone.now().date()
    DailySummary.objects.create(date=date)

    response = client.get(reverse("pulpanalytics:plugin_stats", kwargs={"plugin": plugin}))

    assert response.status_code == 200
    print(date)
    print(response.content)
    assert response.json() == {"labels": [], "datasets": []}


@pytest.mark.parametrize("plugin", PLUGINS[0:2])
def test_xy_data(db, client, plugin):
    date1 = timezone.now().date()
    date2 = date1 - timezone.timedelta(days=1)
    ds1 = DailySummary.objects.create(date=date1)
    ds1.xyversioncount_set.create(name=plugin, version="1.2", count=1)
    ds1.xyversioncount_set.create(name=plugin, version="1.4", count=2)
    ds1.xyversioncount_set.create(name="other_plugin", version="1.5", count=7)
    ds1.xyversioncount_set.create(name=plugin, version="2.0", count=3)
    ds1.xyversioncount_set.create(name="other_plugin", version="2.3", count=6)
    ds1.xyversioncount_set.create(name=plugin, version="0.5", count=4)
    ds1.xyversioncount_set.create(name=plugin, version="2.3", count=5)
    ds2 = DailySummary.objects.create(date=date2)
    ds2.xyversioncount_set.create(name=plugin, version="1.2", count=2)
    ds2.xyversioncount_set.create(name=plugin, version="1.3", count=1)

    response = client.get(reverse("pulpanalytics:plugin_stats", kwargs={"plugin": plugin}))

    assert response.status_code == 200
    assert response.json() == {
        "labels": [str(date2), str(date1)],
        "datasets": [
            {"data": [0, 5], "fill": "origin", "label": "2.3"},
            {"data": [0, 3], "fill": "-1", "label": "2.0"},
            {"data": [0, 2], "fill": "-1", "label": "1.4"},
            {"data": [1, 0], "fill": "-1", "label": "1.3"},
            {"data": [2, 1], "fill": "-1", "label": "1.2"},
            {"data": [0, 4], "fill": "-1", "label": "0.5"},
        ],
    }


@pytest.mark.parametrize("plugin", PLUGINS[0:2])
def test_xyz_data(db, client, plugin):
    date1 = timezone.now().date()
    date2 = date1 - timezone.timedelta(days=1)
    ds1 = DailySummary.objects.create(date=date1)
    ds1.xyzversioncount_set.create(name=plugin, version="1.4.2", count=1)
    ds1.xyzversioncount_set.create(name=plugin, version="1.4.3", count=2)
    ds1.xyzversioncount_set.create(name="other_plugin", version="1.5.5", count=7)
    ds1.xyzversioncount_set.create(name=plugin, version="2.0.4", count=3)
    ds1.xyzversioncount_set.create(name="other_plugin", version="2.3.0", count=6)
    ds1.xyzversioncount_set.create(name=plugin, version="0.5.1", count=4)
    ds1.xyzversioncount_set.create(name=plugin, version="2.3.0", count=5)
    ds2 = DailySummary.objects.create(date=date2)
    ds2.xyzversioncount_set.create(name=plugin, version="1.4.3", count=2)
    ds2.xyzversioncount_set.create(name=plugin, version="1.4.4", count=1)

    response = client.get(
        reverse("pulpanalytics:plugin_stats", kwargs={"plugin": plugin}) + "?z_stream=1"
    )

    assert response.status_code == 200
    assert response.json() == {
        "labels": [str(date2), str(date1)],
        "datasets": [
            {"data": [0, 5], "fill": "origin", "label": "2.3.0"},
            {"data": [0, 3], "fill": "-1", "label": "2.0.4"},
            {"data": [1, 0], "fill": "-1", "label": "1.4.4"},
            {"data": [2, 2], "fill": "-1", "label": "1.4.3"},
            {"data": [0, 1], "fill": "-1", "label": "1.4.2"},
            {"data": [0, 4], "fill": "-1", "label": "0.5.1"},
        ],
    }

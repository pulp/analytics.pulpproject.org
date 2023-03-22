import pytest
from django.urls import reverse
from django.utils import timezone

from pulpanalytics.models import DailySummary
from pulpanalytics.summary_pb2 import Summary
from pulpanalytics.views import PLUGINS


@pytest.mark.parametrize("plugin", PLUGINS[0:2])
def test_empty_summary(db, client, plugin):
    response = client.get(reverse("pulpanalytics:plugin_stats", kwargs={"plugin": plugin}))

    assert response.status_code == 200
    assert response.json() == {"labels": [], "datasets": []}


@pytest.mark.parametrize("plugin", PLUGINS[0:2])
def test_no_data(db, client, plugin):
    date = timezone.now().date()
    summary = Summary()
    DailySummary.objects.create(date=date, summary=summary)

    response = client.get(reverse("pulpanalytics:plugin_stats", kwargs={"plugin": plugin}))

    assert response.status_code == 200
    print(date)
    print(response.content)
    assert response.json() == {"labels": [str(date)], "datasets": []}


@pytest.mark.parametrize("plugin", PLUGINS[0:2])
def test_xy_data(db, client, plugin):
    date = timezone.now().date()
    summary = Summary()
    xy_component = summary.xy_component
    xy_component.add(name=plugin, version="1.2", count=1)
    xy_component.add(name=plugin, version="1.4", count=2)
    xy_component.add(name="other_plugin", version="1.5", count=7)
    xy_component.add(name=plugin, version="2.0", count=3)
    xy_component.add(name="other_plugin", version="2.3", count=6)
    xy_component.add(name=plugin, version="0.5", count=4)
    xy_component.add(name=plugin, version="2.3", count=5)
    DailySummary.objects.create(date=date, summary=summary)

    response = client.get(reverse("pulpanalytics:plugin_stats", kwargs={"plugin": plugin}))

    assert response.status_code == 200
    assert response.json() == {
        "labels": [str(date)],
        "datasets": [
            {"data": [5], "fill": "origin", "label": "2.3"},
            {"data": [3], "fill": "-1", "label": "2.0"},
            {"data": [2], "fill": "-1", "label": "1.4"},
            {"data": [1], "fill": "-1", "label": "1.2"},
            {"data": [4], "fill": "-1", "label": "0.5"},
        ],
    }


@pytest.mark.parametrize("plugin", PLUGINS[0:2])
def test_xyz_data(db, client, plugin):
    date = timezone.now().date()
    summary = Summary()
    xyz_component = summary.xyz_component
    xyz_component.add(name=plugin, version="1.4.2", count=1)
    xyz_component.add(name=plugin, version="1.4.3", count=2)
    xyz_component.add(name="other_plugin", version="1.5.5", count=7)
    xyz_component.add(name=plugin, version="2.0.4", count=3)
    xyz_component.add(name="other_plugin", version="2.3.0", count=6)
    xyz_component.add(name=plugin, version="0.5.1", count=4)
    xyz_component.add(name=plugin, version="2.3.0", count=5)
    DailySummary.objects.create(date=date, summary=summary)

    response = client.get(
        reverse("pulpanalytics:plugin_stats", kwargs={"plugin": plugin}) + "?z_stream=1"
    )

    assert response.status_code == 200
    assert response.json() == {
        "labels": [str(date)],
        "datasets": [
            {"data": [5], "fill": "origin", "label": "2.3.0"},
            {"data": [3], "fill": "-1", "label": "2.0.4"},
            {"data": [2], "fill": "-1", "label": "1.4.3"},
            {"data": [1], "fill": "-1", "label": "1.4.2"},
            {"data": [4], "fill": "-1", "label": "0.5.1"},
        ],
    }

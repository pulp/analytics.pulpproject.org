import pytest
from django.urls import reverse
from django.utils import timezone

from pulpanalytics.analytics_pb2 import Analytics
from pulpanalytics.models import Component, System

SYSTEM_ID = "00000000000000000000000000000000"


@pytest.fixture(params=[True, False])
def collect_dev_systems(request, settings):
    settings.COLLECT_DEV_SYSTEMS = request.param
    return request.param


def test_system_reports_twice(monkeypatch, db, client):
    analytics = Analytics()
    analytics.system_id = SYSTEM_ID

    yesterday = timezone.now() - timezone.timedelta(days=1)
    with monkeypatch.context() as mp:
        mp.setattr(timezone, "now", lambda: yesterday)
        response = client.post(
            reverse("pulpanalytics:index"), analytics.SerializeToString(), "application/octets"
        )
    assert response.status_code == 200, response.status_code

    response = client.post(
        reverse("pulpanalytics:index"), analytics.SerializeToString(), "application/octets"
    )
    assert response.status_code == 200, response.status_code

    response = client.post(
        reverse("pulpanalytics:index"), analytics.SerializeToString(), "application/octets"
    )
    assert response.status_code == 200, response.status_code

    assert System.objects.filter(system_id=SYSTEM_ID).count() == 2


def test_collect_prod_systems(db, client):
    analytics = Analytics()
    analytics.system_id = SYSTEM_ID
    analytics.components.add(name="comp1", version="1.2.3")
    analytics.components.add(name="comp2", version="1.2.3")

    response = client.post(
        reverse("pulpanalytics:index"), analytics.SerializeToString(), "application/octets"
    )
    assert response.status_code == 200, response.status_code

    assert System.objects.filter(system_id=SYSTEM_ID).count() == 1
    assert Component.objects.count() == 2


def test_collect_dev_systems(db, client, collect_dev_systems):
    analytics = Analytics()
    analytics.system_id = SYSTEM_ID
    analytics.components.add(name="comp1", version="1.2.3")
    analytics.components.add(name="comp2", version="1.2.3-dev")

    response = client.post(
        reverse("pulpanalytics:index"), analytics.SerializeToString(), "application/octets"
    )
    assert response.status_code == 200, response.status_code

    if collect_dev_systems:
        assert System.objects.filter(system_id=SYSTEM_ID).count() == 1
        assert Component.objects.count() == 2
    else:
        assert System.objects.filter(system_id=SYSTEM_ID).count() == 0


def test_collect_system_with_rbac(db, client):
    analytics = Analytics()
    analytics.system_id = SYSTEM_ID
    analytics.rbac_stats.users = 1
    analytics.rbac_stats.groups = 2
    analytics.rbac_stats.domains = 3
    analytics.rbac_stats.custom_access_policies = 4
    analytics.rbac_stats.custom_roles = 5

    response = client.post(
        reverse("pulpanalytics:index"), analytics.SerializeToString(), "application/octets"
    )
    assert response.status_code == 200, response.status_code

    system = System.objects.filter(system_id=SYSTEM_ID).get()
    assert system.users == 1
    assert system.groups == 2
    assert system.domains == 3
    assert system.custom_access_policies == 4
    assert system.custom_roles == 5

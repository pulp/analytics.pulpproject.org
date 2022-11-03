from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pulpanalytics.telemetry_pb2 import Telemetry
from pulpanalytics.models import System


SYSTEM_ID = "00000000000000000000000000000000"


def test_system_reports_twice(monkeypatch, db, client):
    telemetry = Telemetry()
    telemetry.system_id = SYSTEM_ID

    yesterday = timezone.now() - timezone.timedelta(days=1)
    with monkeypatch.context() as mp:
        mp.setattr(timezone, "now", lambda : yesterday)
        response = client.post(reverse("pulpanalytics:index"), telemetry.SerializeToString(), "application/octets")
    assert response.status_code == 200, response.status_code

    response = client.post(reverse("pulpanalytics:index"), telemetry.SerializeToString(), "application/octets")
    assert response.status_code == 200, response.status_code

    response = client.post(reverse("pulpanalytics:index"), telemetry.SerializeToString(), "application/octets")
    assert response.status_code == 200, response.status_code

    assert System.objects.filter(system_id=SYSTEM_ID).count() == 2

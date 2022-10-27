from django.test import TestCase
from django.urls import reverse

from pulpanalytics.telemetry_pb2 import Telemetry
from pulpanalytics.models import System


SYSTEM_ID = "00000000000000000000000000000000"


class ReceiveTelemetryTests(TestCase):
    def test_system_reports_twice(self):
        telemetry = Telemetry()
        telemetry.system_id = SYSTEM_ID
        response = self.client.post(reverse("pulpanalytics:index"), telemetry.SerializeToString(), "application/octets")
        assert response.status_code == 200, response.status_code
        response = self.client.post(reverse("pulpanalytics:index"), telemetry.SerializeToString(), "application/octets")
        assert response.status_code == 200, response.status_code
        assert System.objects.filter(system_id=SYSTEM_ID).count() == 2

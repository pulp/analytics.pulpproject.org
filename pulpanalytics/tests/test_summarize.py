import uuid

import pytest
from django.core.management import call_command
from django.utils import timezone

from pulpanalytics.models import DailySummary, OnlineWorkers, System
from pulpanalytics.summary_pb2 import Summary

SYSTEM_ID = "00000000000000000000000000000000"


@pytest.fixture(params=[0, 1])
def persistent_min_age_days(request, settings):
    settings.PERSISTENT_MIN_AGE_DAYS = request.param
    return request.param


def test_summary_no_system(db):
    assert not DailySummary.objects.exists()
    with pytest.raises(SystemExit):
        call_command("summarize")
    assert not DailySummary.objects.exists()


def test_summary_first_day_empty(db):
    assert not DailySummary.objects.exists()
    System.objects.create(system_id=SYSTEM_ID, postgresql_version=0)
    call_command("summarize")
    assert not DailySummary.objects.exists()


def test_summary_empty(db):
    assert not DailySummary.objects.exists()
    DailySummary.objects.create(date=timezone.now() - timezone.timedelta(days=1), summary=Summary())
    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary
    assert daily_summary.summary == Summary()


def test_summary_age(monkeypatch, db, persistent_min_age_days):
    assert not DailySummary.objects.exists()
    yesterday = timezone.now() - timezone.timedelta(days=1)
    with monkeypatch.context() as mp:
        mp.setattr(timezone, "now", lambda: yesterday)
        System.objects.create(system_id=SYSTEM_ID, postgresql_version=0)

    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary
    assert daily_summary.summary.age_count == [Summary.AgeCount(age=0, count=1)]


def test_summary_worker_count(monkeypatch, db, persistent_min_age_days):
    assert not DailySummary.objects.exists()
    yesterday = timezone.now() - timezone.timedelta(days=1)
    with monkeypatch.context() as mp:
        mp.setattr(timezone, "now", lambda: yesterday)
        system = System.objects.create(system_id=SYSTEM_ID, postgresql_version=0)
        OnlineWorkers.objects.create(system=system, hosts=1, processes=2)

    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary
    if persistent_min_age_days == 1:
        assert daily_summary.summary.online_workers == Summary.OnlineWorkers()
    else:
        assert daily_summary.summary.online_workers == Summary.OnlineWorkers(
            processes__avg=2, hosts__avg=1
        )


def test_summary_postgresql_version(monkeypatch, db):
    assert not DailySummary.objects.exists()
    yesterday = timezone.now() - timezone.timedelta(days=1)
    with monkeypatch.context() as mp:
        mp.setattr(timezone, "now", lambda: yesterday)
        System.objects.create(system_id=uuid.uuid4(), postgresql_version=0)
        System.objects.create(system_id=uuid.uuid4(), postgresql_version=90200)
        System.objects.create(system_id=uuid.uuid4(), postgresql_version=90200)
        System.objects.create(system_id=uuid.uuid4(), postgresql_version=100001)

    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary

    expected_postgresql_version = [
        Summary.PostgresqlVersion(version=0, count=1),
        Summary.PostgresqlVersion(version=90200, count=2),
        Summary.PostgresqlVersion(version=100001, count=1),
    ]

    assert daily_summary.summary.postgresql_version == expected_postgresql_version

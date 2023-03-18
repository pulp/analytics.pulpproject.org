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


def test_summary_age(yesterday, db, persistent_min_age_days):
    assert not DailySummary.objects.exists()
    with yesterday():
        System.objects.create(system_id=SYSTEM_ID, postgresql_version=0)

    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary
    assert daily_summary.summary.age_count == [Summary.AgeCount(age=0, count=1)]


def test_summary_worker_count(yesterday, db, persistent_min_age_days):
    assert not DailySummary.objects.exists()
    with yesterday():
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


def test_summary_postgresql_version(yesterday, db):
    assert not DailySummary.objects.exists()
    with yesterday():
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


def test_summary_rbac(yesterday, db):
    assert not DailySummary.objects.exists()
    with yesterday():
        System.objects.create(
            system_id=uuid.uuid4(),
            users=None,
            groups=None,
            domains=None,
            custom_access_policies=None,
            custom_roles=None,
        )
        System.objects.create(
            system_id=uuid.uuid4(),
            users=1,
            groups=1,
            domains=1,
            custom_access_policies=1,
            custom_roles=1,
        )
        System.objects.create(
            system_id=uuid.uuid4(),
            users=1,
            groups=2,
            domains=2,
            custom_access_policies=2,
            custom_roles=2,
        )
        System.objects.create(
            system_id=uuid.uuid4(),
            users=1,
            groups=2,
            domains=3,
            custom_access_policies=3,
            custom_roles=3,
        )
        System.objects.create(
            system_id=uuid.uuid4(),
            users=1,
            groups=2,
            domains=3,
            custom_access_policies=4,
            custom_roles=4,
        )
        System.objects.create(
            system_id=uuid.uuid4(),
            users=1,
            groups=2,
            domains=3,
            custom_access_policies=4,
            custom_roles=5,
        )

    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary

    expected_rbac_stats = Summary.RbacStats(
        users=[
            Summary.NumberCount(number=1, count=5),
        ],
        groups=[
            Summary.NumberCount(number=1, count=1),
            Summary.NumberCount(number=2, count=4),
        ],
        domains=[
            Summary.NumberCount(number=1, count=1),
            Summary.NumberCount(number=2, count=1),
            Summary.NumberCount(number=3, count=3),
        ],
        custom_access_policies=[
            Summary.NumberCount(number=1, count=1),
            Summary.NumberCount(number=2, count=1),
            Summary.NumberCount(number=3, count=1),
            Summary.NumberCount(number=4, count=2),
        ],
        custom_roles=[
            Summary.NumberCount(number=1, count=1),
            Summary.NumberCount(number=2, count=1),
            Summary.NumberCount(number=3, count=1),
            Summary.NumberCount(number=4, count=1),
            Summary.NumberCount(number=5, count=1),
        ],
    )

    assert daily_summary.summary.rbac_stats == expected_rbac_stats

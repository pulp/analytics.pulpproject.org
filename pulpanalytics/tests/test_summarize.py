import uuid

import pytest
from django.core.management import call_command
from django.utils import timezone

from pulpanalytics.models import DailySummary, System

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
    DailySummary.objects.create(date=timezone.now() - timezone.timedelta(days=1))
    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary


def test_summary_age(yesterday, db, persistent_min_age_days):
    assert not DailySummary.objects.exists()
    with yesterday():
        System.objects.create(system_id=SYSTEM_ID, postgresql_version=0)

    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary
    assert list(daily_summary.agecount_set.values("age", "count")) == [{"age": 0, "count": 1}]


def test_summary_worker_count(yesterday, db, persistent_min_age_days):
    assert not DailySummary.objects.exists()
    with yesterday():
        System.objects.create(
            system_id=uuid.uuid4(), postgresql_version=0, worker_hosts=1, worker_processes=2
        )
        System.objects.create(system_id=uuid.uuid4(), postgresql_version=0)

    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary
    if persistent_min_age_days >= 1:
        assert daily_summary.deploymentstats.online_worker_processes_avg is None
        assert daily_summary.deploymentstats.online_worker_hosts_avg is None
        assert daily_summary.deploymentstats.online_content_app_processes_avg is None
        assert daily_summary.deploymentstats.online_content_app_hosts_avg is None
    else:
        assert daily_summary.deploymentstats.online_worker_processes_avg == 2
        assert daily_summary.deploymentstats.online_worker_hosts_avg == 1.0
        assert daily_summary.deploymentstats.online_content_app_processes_avg is None
        assert daily_summary.deploymentstats.online_content_app_hosts_avg is None


def test_summary_component_versions(yesterday, db):
    assert not DailySummary.objects.exists()
    with yesterday():
        system1 = System.objects.create(system_id=uuid.uuid4())
        system1.component_set.create(name="plugin1", version="1.0.0")
        system1.component_set.create(name="plugin2", version="2.0.0")
        system2 = System.objects.create(system_id=uuid.uuid4())
        system2.component_set.create(name="plugin1", version="1.0.0")
        system2.component_set.create(name="plugin3", version="3.0.0")
        system3 = System.objects.create(system_id=uuid.uuid4())
        system3.component_set.create(name="plugin1", version="1.0.1")
        system3.component_set.create(name="plugin4", version="4.0.0")
        System.objects.create(system_id=uuid.uuid4())

    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary

    assert daily_summary.xyversioncount_set.count() == 4
    assert daily_summary.xyversioncount_set.get(name="plugin1", version="1.0").count == 3
    assert daily_summary.xyversioncount_set.get(name="plugin2", version="2.0").count == 1
    assert daily_summary.xyversioncount_set.get(name="plugin3", version="3.0").count == 1
    assert daily_summary.xyversioncount_set.get(name="plugin4", version="4.0").count == 1
    assert daily_summary.xyzversioncount_set.count() == 5
    assert daily_summary.xyzversioncount_set.get(name="plugin1", version="1.0.0").count == 2
    assert daily_summary.xyzversioncount_set.get(name="plugin1", version="1.0.1").count == 1
    assert daily_summary.xyzversioncount_set.get(name="plugin2", version="2.0.0").count == 1
    assert daily_summary.xyzversioncount_set.get(name="plugin3", version="3.0.0").count == 1
    assert daily_summary.xyzversioncount_set.get(name="plugin4", version="4.0.0").count == 1


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

    assert list(
        daily_summary.postgresversioncount_set.order_by("version").values("version", "count")
    ) == [
        {"version": 0, "count": 1},
        {"version": 90200, "count": 2},
        {"version": 100001, "count": 1},
    ]


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

    assert list(
        daily_summary.numbercount_set.filter(name="users")
        .order_by("count")
        .values("number", "count")
    ) == [
        {"number": 1, "count": 5},
    ]
    assert list(
        daily_summary.numbercount_set.filter(name="groups")
        .order_by("count")
        .values("number", "count")
    ) == [
        {"number": 1, "count": 1},
        {"number": 2, "count": 4},
    ]
    assert list(
        daily_summary.numbercount_set.filter(name="domains")
        .order_by("count")
        .values("number", "count")
    ) == [
        {"number": 1, "count": 1},
        {"number": 2, "count": 1},
        {"number": 3, "count": 3},
    ]
    assert list(
        daily_summary.numbercount_set.filter(name="custom_access_policies")
        .order_by("count")
        .values("number", "count")
    ) == [
        {"number": 1, "count": 1},
        {"number": 2, "count": 1},
        {"number": 3, "count": 1},
        {"number": 4, "count": 2},
    ]
    assert list(
        daily_summary.numbercount_set.filter(name="custom_roles")
        .order_by("count")
        .values("number", "count")
    ) == [
        {"number": 1, "count": 1},
        {"number": 2, "count": 1},
        {"number": 3, "count": 1},
        {"number": 4, "count": 1},
        {"number": 5, "count": 1},
    ]

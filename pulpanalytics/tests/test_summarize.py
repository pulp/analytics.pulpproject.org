import pytest
from django.utils import timezone
from django.core.management import call_command

from pulpanalytics.models import DailySummary, System


SYSTEM_ID = "00000000000000000000000000000000"


def test_summary_no_system(db):
    assert not DailySummary.objects.exists()
    with pytest.raises(SystemExit):
        call_command("summarize")
    assert not DailySummary.objects.exists()


def test_summary_first_day_empty(db):
    assert not DailySummary.objects.exists()
    System.objects.create(system_id=SYSTEM_ID)
    call_command("summarize")
    assert not DailySummary.objects.exists()


def test_summary_empty(db):
    assert not DailySummary.objects.exists()
    DailySummary.objects.create(
        date=timezone.now() - timezone.timedelta(days=1), summary={}
    )
    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary
    assert daily_summary.summary == {}


def test_summary_age(monkeypatch, db):
    assert not DailySummary.objects.exists()
    yesterday = timezone.now() - timezone.timedelta(days=1)
    with monkeypatch.context() as mp:
        mp.setattr(timezone, "now", lambda : yesterday)
        System.objects.create(system_id=SYSTEM_ID)

    call_command("summarize")
    daily_summary = DailySummary.objects.order_by("date").last()
    assert daily_summary
    assert daily_summary.summary["ageCount"] == [{"age": 0, "count": 1}]

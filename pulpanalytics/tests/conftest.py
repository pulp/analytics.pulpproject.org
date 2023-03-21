import contextlib

import pytest
from django.utils import timezone


@pytest.fixture
def yesterday(monkeypatch):
    @contextlib.contextmanager
    def _yesterday(days=1):
        yesterday = timezone.now() - timezone.timedelta(days=days)
        with monkeypatch.context() as mp:
            mp.setattr(timezone, "now", lambda: yesterday)
            yield mp

    return _yesterday

import pytest
from django.urls import reverse

from pulpanalytics.views import RootView, _get_postgresql_version_string_from_int


def test_empty_summary(db, rf):
    request = rf.get(reverse("pulpanalytics:index"))
    response = RootView.as_view()(request)

    assert response.status_code == 200, response.status_code
    assert b"<title>" in response.content
    assert b'<meta name="revision"' in response.content


@pytest.mark.parametrize(
    "postgresql_int, version_str",
    [(0, "Unknown"), (100001, "10.1"), (110000, "11.0"), (90105, "9.1.5"), (90200, "9.2.0")],
)
def test_postgresql_int_to_version_translation(postgresql_int, version_str):
    assert _get_postgresql_version_string_from_int(postgresql_int) == version_str

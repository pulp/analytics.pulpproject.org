from django.urls import reverse

from pulpanalytics.views import RootView


def test_empty_summary(db, rf):
    request = rf.get(reverse("pulpanalytics:index"))
    response = RootView.as_view()(request)

    assert response.status_code == 200, response.status_code
    assert b"<title>" in response.content
    assert b'<meta name="revision"' in response.content

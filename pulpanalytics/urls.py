from django.urls import path

from pulpanalytics.views import RootView

app_name = "pulpanalytics"
urlpatterns = [
    path("", RootView.as_view(), name="index"),
]

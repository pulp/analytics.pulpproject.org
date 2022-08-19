from django.urls import path

from pulpanalytics.views import RootView

urlpatterns = [
    path("", RootView.as_view()),
]

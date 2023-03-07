from django.urls import path

from pulpanalytics.views import RootView, rbac_stats_view

app_name = "pulpanalytics"
urlpatterns = [
    path("", RootView.as_view(), name="index"),
    path("rbac_stats/<str:measure>/", rbac_stats_view, name="rbac_stats"),
]

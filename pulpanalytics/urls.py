from django.urls import path

from pulpanalytics.views import RootView, plugin_stats_view, rbac_stats_view

app_name = "pulpanalytics"
urlpatterns = [
    path("", RootView.as_view(), name="index"),
    path("plugin_stats/<str:plugin>/", plugin_stats_view, name="plugin_stats"),
    path("rbac_stats/<str:measure>/", rbac_stats_view, name="rbac_stats"),
]

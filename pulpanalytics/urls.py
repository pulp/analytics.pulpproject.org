from django.urls import path

from pulpanalytics.views import (
    RootView,
    demography_view,
    deployment_stats_view,
    plugin_stats_view,
    postgresql_versions_view,
    rbac_stats_view,
    systems_by_age_view,
)

app_name = "pulpanalytics"
urlpatterns = [
    path("", RootView.as_view(), name="index"),
    path("deployment_stats/<str:component>/", deployment_stats_view, name="deployment_stats"),
    path("plugin_stats/<str:plugin>/", plugin_stats_view, name="plugin_stats"),
    path("postgresql_versions/", postgresql_versions_view, name="postgresql_versions"),
    path("demography/", demography_view, name="demography"),
    path("systems_by_age/", systems_by_age_view, name="systems_by_age"),
    path("rbac_stats/<str:measure>/", rbac_stats_view, name="rbac_stats"),
]

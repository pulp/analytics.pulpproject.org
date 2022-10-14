from import_export import resources

from pulpanalytics.models import Component, DailySummary, OnlineContentApps, OnlineWorkers, System


class ComponentResource(resources.ModelResource):

    class Meta:
        model = Component


class DailySummaryResource(resources.ModelResource):

    class Meta:
        model = DailySummary


class OnlineContentAppsResource(resources.ModelResource):

    class Meta:
        model = OnlineContentApps


class OnlineWorkersResource(resources.ModelResource):

    class Meta:
        model = OnlineWorkers


class SystemResource(resources.ModelResource):

    class Meta:
        model = System

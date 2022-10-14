from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from pulpanalytics.import_export_resources import ComponentResource, DailySummaryResource, OnlineContentAppsResource, OnlineWorkersResource, SystemResource
from pulpanalytics.models import Component, DailySummary, OnlineContentApps, OnlineWorkers, System


class ComponentAdmin(ImportExportModelAdmin):
    resource_class = ComponentResource


class DailySummaryAdmin(ImportExportModelAdmin):
    resource_class = DailySummaryResource


class OnlineContentAppsAdmin(ImportExportModelAdmin):
    resource_class = OnlineContentAppsResource


class OnlineWorkersAdmin(ImportExportModelAdmin):
    resource_class = OnlineWorkersResource


class SystemAdmin(ImportExportModelAdmin):
    resource_class = SystemResource


admin.site.register(Component, ComponentAdmin)
admin.site.register(DailySummary, DailySummaryAdmin)
admin.site.register(OnlineContentApps, OnlineContentAppsAdmin)
admin.site.register(OnlineWorkers, OnlineWorkersAdmin)
admin.site.register(System, SystemAdmin)

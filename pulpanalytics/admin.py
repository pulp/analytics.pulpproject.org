from django.contrib import admin

from pulpanalytics.models import Component, DailySummary, OnlineContentApps, OnlineWorkers, System


admin.site.register(Component)
admin.site.register(DailySummary)
admin.site.register(OnlineContentApps)
admin.site.register(OnlineWorkers)
admin.site.register(System)

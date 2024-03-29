import io

from django.contrib import admin
from django.core.management import call_command
from django.template.response import TemplateResponse
from django.urls import path

from pulpanalytics.models import (
    AgeCount,
    Component,
    DailySummary,
    DeploymentStats,
    NumberCount,
    PostgresVersionCount,
    System,
    XYVersionCount,
    XYZVersionCount,
)

admin.site.register(AgeCount)
admin.site.register(Component)
admin.site.register(DeploymentStats)
admin.site.register(NumberCount)
admin.site.register(PostgresVersionCount)
admin.site.register(System)
admin.site.register(XYVersionCount)
admin.site.register(XYZVersionCount)


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    def get_urls(self):
        return [
            path("add/", self.admin_site.admin_view(self.summarize)),
        ] + super().get_urls()

    def summarize(self, request):
        context = {}
        stdout_stream = io.StringIO()
        try:
            call_command("summarize", stdout=stdout_stream)
        except SystemExit as e:
            context["errors"] = str(e)
        context["stdout"] = stdout_stream.getvalue()
        return TemplateResponse(request, "pulpanalytics/summarize.html", context)

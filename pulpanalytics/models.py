from django.db import models

from pulpanalytics.fields import ProtoBufField
from pulpanalytics.summary_pb2 import Summary


class System(models.Model):
    system_id = models.UUIDField()
    created = models.DateTimeField(auto_now_add=True)
    first_seen = models.DateTimeField()

    def __str__(self):
        return f"SystemID={self.system_id}, Created={self.created}"

    class Meta:
        constraints=[
            models.UniqueConstraint(
                "system_id",
                models.functions.TruncDay("created"),
                name="unique_system_checkin_per_day",
            ),
        ]


class Component(models.Model):
    name = models.TextField()
    version = models.TextField()
    system = models.ForeignKey(System, on_delete=models.CASCADE)

    def __str__(self):
        return f"SystemID={self.system.system_id}, Name={self.name}, Version={self.version}"


class OnlineContentApps(models.Model):
    processes = models.IntegerField()
    hosts = models.IntegerField()
    system = models.ForeignKey(System, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "online content apps"

    def __str__(self):
        return f"SystemID={self.system.system_id}, Processes={self.processes}, Hosts={self.hosts}"


class OnlineWorkers(models.Model):
    processes = models.IntegerField()
    hosts = models.IntegerField()
    system = models.ForeignKey(System, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "online workers"

    def __str__(self):
        return f"SystemID={self.system.system_id}, Processes={self.processes}, Hosts={self.hosts}"


class DailySummary(models.Model):
    date = models.DateField(unique=True)
    summary = ProtoBufField(serializer=Summary)

    class Meta:
        verbose_name_plural = "daily summaries"

    def __str__(self):
        return f"Summary for {self.date}"

    def epoch_ms_timestamp(self):
        return int(self.date.strftime('%s')) * 1000

    def online_workers_hosts_avg_data_point(self):
        return {
            "x": self.epoch_ms_timestamp(),
            "y": self.summary.online_workers.hosts__avg
        }

    def online_workers_processes_avg_data_point(self):
        return {
            "x": self.epoch_ms_timestamp(),
            "y": self.summary.online_workers.processes__avg
        }

    def online_content_apps_hosts_avg_data_point(self):
        return {
            "x": self.epoch_ms_timestamp(),
            "y": self.summary.online_content_apps.hosts__avg
        }

    def online_content_apps_processes_avg_data_point(self):
        return {
            "x": self.epoch_ms_timestamp(),
            "y": self.summary.online_content_apps.processes__avg
        }

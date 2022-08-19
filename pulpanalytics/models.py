from django.db import models


class System(models.Model):
    system_id = models.UUIDField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SystemID={self.id}, Created={self.created}"


class Component(models.Model):
    name = models.TextField()
    version = models.TextField()
    system = models.ForeignKey(System, on_delete=models.CASCADE)

    def __str__(self):
        return f"SystemID={self.id}, Name={self.name}, Version={self.version}"


class OnlineContentApps(models.Model):
    processes = models.IntegerField()
    hosts = models.IntegerField()
    system = models.ForeignKey(System, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "online content apps"

    def __str__(self):
        return f"System={self.system.id}, Processes={self.processes}, Hosts={self.hosts}"


class OnlineWorkers(models.Model):
    processes = models.IntegerField()
    hosts = models.IntegerField()
    system = models.ForeignKey(System, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "online workers"

    def __str__(self):
        return f"System={self.system.id}, Processes={self.processes}, Hosts={self.hosts}"


class DailySummary(models.Model):
    date = models.DateField(unique=True)
    summary = models.JSONField()

    class Meta:
        verbose_name_plural = "daily summaries"

    def __str__(self):
        return f"Summary for {self.date}"

    def epoch_ms_timestamp(self):
        return int(self.date.strftime('%s')) * 1000

    def online_workers_hosts_avg_data_point(self):
        return {
            "x": self.epoch_ms_timestamp(),
            "y": self.summary["onlineWorkers"]["hostsAvg"]
        }

    def online_workers_processes_avg_data_point(self):
        return {
            "x": self.epoch_ms_timestamp(),
            "y": self.summary["onlineWorkers"]["processesAvg"]
        }

    def online_content_apps_hosts_avg_data_point(self):
        return {
            "x": self.epoch_ms_timestamp(),
            "y": self.summary["onlineContentApps"]["hostsAvg"]
        }

    def online_content_apps_processes_avg_data_point(self):
        return {
            "x": self.epoch_ms_timestamp(),
            "y": self.summary["onlineContentApps"]["processesAvg"]
        }

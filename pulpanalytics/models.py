from django.db import models

from pulpanalytics.fields import ProtoBufField
from pulpanalytics.summary_pb2 import Summary


class System(models.Model):
    system_id = models.UUIDField()
    created = models.DateTimeField(auto_now_add=True)
    first_seen = models.DateTimeField()
    postgresql_version = models.PositiveIntegerField(default=0)
    users = models.PositiveIntegerField(null=True)
    groups = models.PositiveIntegerField(null=True)
    domains = models.PositiveIntegerField(null=True)
    custom_access_policies = models.PositiveIntegerField(null=True)
    custom_roles = models.PositiveIntegerField(null=True)
    content_app_processes = models.PositiveIntegerField(null=True)
    content_app_hosts = models.PositiveIntegerField(null=True)
    worker_processes = models.PositiveIntegerField(null=True)
    worker_hosts = models.PositiveIntegerField(null=True)

    def __str__(self):
        return f"SystemID={self.system_id}, Created={self.created}"

    class Meta:
        constraints = [
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

    class Meta:
        unique_together = [("system", "name")]
        indexes = [models.Index(fields=["name"])]


class DailySummary(models.Model):
    date = models.DateField(primary_key=True)
    summary = ProtoBufField(serializer=Summary)

    class Meta:
        verbose_name_plural = "daily summaries"

    def __str__(self):
        return f"Summary for {self.date}"


class DeploymentStats(models.Model):
    summary = models.OneToOneField(DailySummary, on_delete=models.CASCADE, primary_key=True)
    online_worker_hosts_avg = models.FloatField(null=True, blank=True)
    online_worker_processes_avg = models.FloatField(null=True, blank=True)
    online_content_app_hosts_avg = models.FloatField(null=True, blank=True)
    online_content_app_processes_avg = models.FloatField(null=True, blank=True)


class PostgresVersionCount(models.Model):
    summary = models.ForeignKey(DailySummary, on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    count = models.PositiveIntegerField()

    @property
    def pretty_version(self):
        """See https://www.postgresql.org/docs/current/libpq-status.html#LIBPQ-PQSERVERVERSION"""
        if self.version == 0:
            return "Unknown"
        if self.version >= 100000:  # It's 10.0+
            major_version = self.version // 10000
            minor_version = self.version % 10000
            return f"{major_version}.{minor_version}"
        else:  # It's < 10.0
            version_str = f"{self.version:05}"
            major_version = int(version_str[:1])
            minor_version = int(version_str[1:3])
            bugfix_version = int(version_str[3:])
            return f"{major_version}.{minor_version}.{bugfix_version}"

    def __str__(self):
        return f"PostgreSQL version {self.pretty_version} date={self.summary_id} count={self.count}"

    class Meta:
        unique_together = (("summary", "version"),)
        indexes = [models.Index(fields=["summary"])]


class XYVersionCount(models.Model):
    summary = models.ForeignKey(DailySummary, on_delete=models.CASCADE)
    name = models.TextField()
    version = models.TextField()
    count = models.PositiveIntegerField()

    class Meta:
        unique_together = (("summary", "name", "version"),)
        indexes = [models.Index(fields=["summary", "name"])]


class XYZVersionCount(models.Model):
    summary = models.ForeignKey(DailySummary, on_delete=models.CASCADE)
    name = models.TextField()
    version = models.TextField()
    count = models.PositiveIntegerField()

    class Meta:
        unique_together = (("summary", "name", "version"),)
        indexes = [models.Index(fields=["summary", "name"])]

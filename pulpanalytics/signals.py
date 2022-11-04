from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from pulpanalytics.models import System


@receiver(pre_save, sender=System)
def _system_pre_save(sender, instance, raw, **kwargs):
    # `raw` imports should not do any database queries.
    if not raw:
        assert instance.system_id, "System needs a unique id."
        first_seen_system = (
            System.objects.filter(system_id=instance.system_id).order_by("first_seen").first()
        )
        if first_seen_system is None:
            instance.first_seen = timezone.now()
        else:
            instance.first_seen = first_seen_system.first_seen

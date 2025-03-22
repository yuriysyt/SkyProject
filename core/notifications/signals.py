from django.dispatch import receiver
from django.db.models.signals import post_save
from core.models import HealthCheck
from core.notifications.models import Notification

@receiver(post_save, sender=HealthCheck)
def notify_low_health_score(sender, instance, created, **kwargs):
    if created and instance.score <= 2:
        # Create notification for low health score
        Notification.objects.create(
            user=instance.department.manager,
            type='warning',
            message=f'Low health score ({instance.score}) reported for {instance.category.name} in {instance.department.name}'
        )


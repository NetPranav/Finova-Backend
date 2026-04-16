from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GroupMember, GroupMessage, Vote


@receiver(post_save, sender=GroupMember)
def create_join_system_message(sender, instance, created, **kwargs):
    """Auto-generate a system message when a user joins a group."""
    if created and instance.is_active:
        GroupMessage.objects.create(
            group=instance.group,
            sender=None,
            content=f"{instance.user.username} joined the group.",
            message_type='system',
        )


@receiver(post_save, sender=Vote)
def handle_vote_cast(sender, instance, created, **kwargs):
    """
    After a vote is cast, check for:
    1. Turbo-Reduction eligibility (100% participation → 90% time reduction)
    2. Quorum being met → auto-resolve
    """
    if created:
        poll = instance.poll
        # Turbo-Reduction check
        poll.apply_turbo_reduction()
        # Quorum check
        if poll.quorum_met:
            poll.resolve()

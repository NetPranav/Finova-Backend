from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Actions to perform after user creation
    """
    if created:
        # Set default notification preferences
        if not instance.notification_preferences:
            instance.notification_preferences = {
                'email_notifications': True,
                'push_notifications': True,
                'sms_notifications': False,
                'weekly_digest': True,
                'trade_alerts': True,
                'club_activity': True
            }
        
        # Set default privacy settings
        if not instance.privacy_settings:
            instance.privacy_settings = {
                'profile_visibility': 'public',
                'show_stats': True,
                'show_clubs': True,
                'allow_friend_requests': True
            }
        
        # Save if defaults were added
        if not kwargs.get('raw', False):  # Don't save during fixture loading
            User.objects.filter(pk=instance.pk).update(
                notification_preferences=instance.notification_preferences,
                privacy_settings=instance.privacy_settings
            )
        
        # TODO: Send welcome email
        # TODO: Create default learning path assignment
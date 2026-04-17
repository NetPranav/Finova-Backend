from django.apps import AppConfig


class GroupsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'groups'
    verbose_name = 'Investment Groups'

    def ready(self):
        import groups.signals  # noqa
        
        # Start apscheduler only under main process
        import os
        if os.environ.get('RUN_MAIN', None) != 'true':
            try:
                from . import scheduler
                scheduler.start()
            except Exception:
                pass

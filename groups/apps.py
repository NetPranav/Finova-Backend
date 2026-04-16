from django.apps import AppConfig


class GroupsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'groups'
    verbose_name = 'Investment Groups'

    def ready(self):
        import groups.signals  # noqa

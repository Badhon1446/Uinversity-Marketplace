from django.apps import AppConfig


class MartappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'martapp'

    def ready(self):
        import martapp.signals
from django.apps import AppConfig


class InstructorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'instructors'

    def ready(self):
        import instructors.signals
from django.apps import AppConfig


class DeparaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'depara'
    verbose_name = 'DePara'


default_app_config = 'depara.apps.DeparaConfig'

from django.apps import AppConfig


class DeparaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'entidades.depara'
    verbose_name = 'DePara'


default_app_config = 'entidades.depara.apps.DeparaConfig'

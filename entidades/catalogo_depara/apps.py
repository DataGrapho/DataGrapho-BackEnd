from django.apps import AppConfig


class CatalogoDeparaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'entidades.catalogo_depara'
    verbose_name = 'Catálogo DePara'


default_app_config = 'entidades.catalogo_depara.apps.CatalogoDeparaConfig'

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .controller import CatalogoDeparaViewSet

app_name = "catalogo_depara"

router = DefaultRouter()
router.register(r"", CatalogoDeparaViewSet, basename="catalogo_depara")

urlpatterns = [
    path("", include(router.urls)),
]

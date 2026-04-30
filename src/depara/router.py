from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .controller import DeparaViewSet

app_name = "depara"

router = DefaultRouter()
router.register(r"", DeparaViewSet, basename="depara")

urlpatterns = [
    path("", include(router.urls)),
]

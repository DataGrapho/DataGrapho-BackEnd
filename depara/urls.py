from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeparaViewSet

app_name = 'depara'

router = DefaultRouter()
router.register(r'', DeparaViewSet, basename='depara')

urlpatterns = [
    path('', include(router.urls)),
]

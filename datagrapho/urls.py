"""
Main URL configuration for datagrapho project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/catalogo-depara/', include('entidades.catalogo_depara.urls')),
    path('api/v1/depara/', include('entidades.depara.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

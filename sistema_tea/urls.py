"""
=============================================================================
SISTEMA EXPERTO PARA APOYO PEDAGÓGICO EN TEA
=============================================================================
Archivo: sistema_tea/urls.py
Descripción: URLs raíz del proyecto. Incluye las rutas de la app 'experto',
             las rutas nativas de Django para recuperación de contraseña,
             y los archivos media en modo desarrollo.
=============================================================================
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Administración de Django
    path('admin/', admin.site.urls),

    # Rutas de la aplicación principal
    path('', include('experto.urls')),

    # Rutas de recuperación de contraseña (Django built-in)
    # Provee: /password-reset/, /password-reset/done/,
    #         /reset/<uidb64>/<token>/, /reset/done/
    path('', include('django.contrib.auth.urls')),
]

# Servir archivos media en modo DEBUG (desarrollo)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

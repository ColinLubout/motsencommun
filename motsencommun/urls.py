"""Adresses du site.

L'administration vit au chemin choisi dans la configuration (``CHEMIN_ADMIN``),
jamais à l'adresse par défaut ``/admin/``.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path(settings.CHEMIN_ADMIN, admin.site.urls),
]

"""Adresses du site.

Les pages publiques commencent par le préfixe de leur langue (/fr/, /en/…) ;
le reste du chemin reste en français, quelle que soit la langue.
L'administration vit au chemin choisi dans la configuration (``CHEMIN_ADMIN``),
jamais à l'adresse par défaut ``/admin/``.
"""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.CHEMIN_ADMIN, admin.site.urls),
    *i18n_patterns(path("", include("lexique.urls")), prefix_default_language=True),
]

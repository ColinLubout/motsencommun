"""Adresses du site.

Les pages publiques commencent par le préfixe de leur langue (/fr/, /en/…) ;
le reste du chemin reste en français, quelle que soit la langue.
L'administration vit au chemin choisi dans la configuration (``CHEMIN_ADMIN``),
jamais à l'adresse par défaut ``/admin/``.
"""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from lexique import views as lexique
from motsencommun import views

urlpatterns = [
    path(settings.CHEMIN_ADMIN, admin.site.urls),
    # Pour les robots, sans préfixe de langue.
    path("robots.txt", lexique.robots_txt, name="robots_txt"),
    path("sitemap.xml", lexique.plan_du_site, name="plan_du_site"),
    path(".well-known/security.txt", views.security_txt, name="security_txt"),
    *i18n_patterns(path("", include("lexique.urls")), prefix_default_language=True),
]

# En développement seulement : sur le serveur, Caddy sert /media/ et
# /telechargements/ lui-même.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(
    settings.TELECHARGEMENTS_URL, document_root=settings.DOSSIER_TELECHARGEMENTS
)

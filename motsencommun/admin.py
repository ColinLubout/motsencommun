"""Le site d'administration de Mots en commun."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from motsencommun.connexion import FormulaireConnexion


class SiteAdministration(admin.AdminSite):
    """L'administration de Django, avec la double authentification obligatoire pour le superutilisateur.

    Les relecteurs peuvent l'activer sans y être obligés.
    """

    site_header = "Mots en commun"
    site_title = "Mots en commun"
    index_title = _("Administration")
    login_form = FormulaireConnexion
    login_template = "admin/connexion.html"

    def has_permission(self, request):
        if not super().has_permission(request):
            return False
        if request.user.is_superuser:
            return request.user.is_verified()
        return True

"""Configuration des applications propres au projet."""

from django.contrib.admin.apps import AdminConfig


class AdministrationConfig(AdminConfig):
    """L'application admin de Django, avec notre site d'administration par défaut."""

    default_site = "motsencommun.admin.SiteAdministration"

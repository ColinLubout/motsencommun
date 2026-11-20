"""Configuration de l'application lexique."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LexiqueConfig(AppConfig):
    """Les entrées, leurs pièges, leurs exemples et leurs traductions."""

    name = "lexique"
    verbose_name = _("Lexique")

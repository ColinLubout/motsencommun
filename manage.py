#!/usr/bin/env python
"""Utilitaire en ligne de commande de Django, pour les tâches d'administration du site."""

import os
import sys


def main():
    """Lance la commande Django demandée sur la ligne de commande."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "motsencommun.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as erreur:
        raise ImportError(
            "Django est introuvable. Lancez les commandes avec uv, qui prépare "
            "l'environnement du projet : uv run python manage.py <commande>"
        ) from erreur
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

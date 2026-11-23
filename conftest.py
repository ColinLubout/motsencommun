"""Préparatifs communs à toute la suite de tests."""

import pytest
from django.core.management import call_command

#: Dossiers où « compilemessages » ne cherche pas de traductions.
HORS_DU_PROJET = [".venv", ".git", "donnees", "node_modules"]


@pytest.fixture(autouse=True)
def media_temporaire(settings, tmp_path):
    """Les fichiers que crée le site (images d'aperçu) vont dans un dossier jetable."""
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture(scope="session", autouse=True)
def traductions_compilees():
    """Les .mo ne sont pas dans le dépôt : on les recrée à partir des .po avant les tests."""
    call_command("compilemessages", verbosity=0, ignore_patterns=HORS_DU_PROJET)

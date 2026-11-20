"""Vérifications générales du projet Django."""

import pytest
from django.apps import apps
from django.core.management import call_command


def test_les_verifications_de_django_passent():
    call_command("check", fail_level="WARNING")


@pytest.mark.django_db
def test_aucune_migration_ne_manque():
    """Chaque changement de modèle arrive avec sa migration."""
    call_command("makemigrations", check=True, dry_run=True, verbosity=0)


def test_l_application_lexique_est_installee():
    assert apps.is_installed("lexique")
    assert str(apps.get_app_config("lexique").verbose_name) == "Lexique"

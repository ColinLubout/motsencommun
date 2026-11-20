"""Les réglages viennent des variables d'environnement, et le serveur n'a pas de valeur par défaut."""

from pathlib import Path

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper

OBLIGATOIRES = [
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "CHEMIN_ADMIN",
    "DOSSIER_DONNEES",
]


@pytest.fixture
def variables_serveur(tmp_path):
    """Un jeu complet de variables, comme sur le serveur."""
    return {
        "DJANGO_SECRET_KEY": "une-cle-de-test-assez-longue-pour-ressembler-a-une-vraie-0123456789",
        "DJANGO_ALLOWED_HOSTS": "motsencommun.fr",
        "CHEMIN_ADMIN": "coulisses-4f7k/",
        "DOSSIER_DONNEES": str(tmp_path),
    }


def test_les_reglages_viennent_de_l_environnement(
    charger_reglages, variables_serveur, tmp_path
):
    reglages = charger_reglages(**variables_serveur)
    assert reglages["DEBUG"] is False
    assert reglages["SECRET_KEY"] == variables_serveur["DJANGO_SECRET_KEY"]
    assert reglages["ALLOWED_HOSTS"] == ["motsencommun.fr"]
    assert reglages["CHEMIN_ADMIN"] == "coulisses-4f7k/"
    assert reglages["DATABASES"]["default"]["NAME"] == tmp_path / "base.sqlite3"


def test_le_serveur_ne_demarre_pas_sans_ses_variables(charger_reglages):
    with pytest.raises(ImproperlyConfigured) as erreur:
        charger_reglages()
    for nom in OBLIGATOIRES:
        assert nom in str(erreur.value)


@pytest.mark.parametrize("manquante", OBLIGATOIRES)
def test_chaque_variable_est_obligatoire_sur_le_serveur(
    charger_reglages, variables_serveur, manquante
):
    del variables_serveur[manquante]
    with pytest.raises(ImproperlyConfigured, match=f"manquantes : {manquante}"):
        charger_reglages(**variables_serveur)


def test_le_developpement_local_fonctionne_sans_autre_variable(charger_reglages):
    reglages = charger_reglages(DJANGO_DEBUG="1")
    assert reglages["DEBUG"] is True
    assert reglages["SECRET_KEY"].startswith("django-insecure-")
    assert reglages["CHEMIN_ADMIN"] == "admin/"
    base = Path(settings.BASE_DIR) / "donnees" / "base.sqlite3"
    assert reglages["DATABASES"]["default"]["NAME"] == base


def test_chaque_variable_lue_est_documentee(charger_reglages, variables_documentees):
    reglages = charger_reglages(DJANGO_DEBUG="1")
    assert reglages["env"].lues <= variables_documentees


def test_sqlite_fonctionne_en_mode_wal(tmp_path, django_db_blocker):
    """Une vraie base SQLite ouverte avec nos réglages passe en mode WAL."""
    reglages = dict(
        connections["default"].settings_dict, NAME=tmp_path / "essai.sqlite3"
    )
    connexion = DatabaseWrapper(reglages, alias="essai_wal")
    with django_db_blocker.unblock():
        try:
            with connexion.cursor() as curseur:
                curseur.execute("PRAGMA journal_mode")
                assert curseur.fetchone()[0] == "wal"
        finally:
            connexion.close()
    assert reglages["OPTIONS"]["transaction_mode"] == "IMMEDIATE"


def test_francais_d_abord_et_heure_de_paris():
    assert settings.LANGUAGE_CODE == "fr"
    assert [code for code, _nom in settings.LANGUAGES] == ["fr", "en"]
    assert settings.TIME_ZONE == "Europe/Paris"
    assert settings.USE_TZ is True

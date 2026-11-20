"""Tests de la lecture des variables d'environnement."""

from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from motsencommun.environnement import Environnement


def serveur(**variables):
    """Environnement de production : DJANGO_DEBUG est absent."""
    return Environnement(variables)


def developpement(**variables):
    """Environnement de développement local : DJANGO_DEBUG=1."""
    return Environnement({"DJANGO_DEBUG": "1", **variables})


@pytest.mark.parametrize(
    "valeur", ["1", "true", "True", "yes", "on", "oui", "OUI", "vrai", " 1 "]
)
def test_booleen_vrai(valeur):
    assert Environnement({"X": valeur}).booleen("X", defaut=False) is True


@pytest.mark.parametrize("valeur", ["0", "false", "FALSE", "no", "off", "non", "faux"])
def test_booleen_faux(valeur):
    assert Environnement({"X": valeur}).booleen("X", defaut=True) is False


def test_booleen_absent_ou_vide_prend_la_valeur_par_defaut():
    assert Environnement({}).booleen("X", defaut=True) is True
    assert Environnement({"X": "  "}).booleen("X", defaut=False) is False


def test_booleen_invalide_refuse():
    with pytest.raises(ImproperlyConfigured, match="X vaut « peut-etre »"):
        Environnement({"X": "peut-etre"}).booleen("X", defaut=False)


def test_le_mode_developpement_est_desactive_par_defaut():
    assert serveur().developpement is False
    assert developpement().developpement is True


def test_obligatoire_present():
    env = serveur(CLE="  valeur  ")
    assert env.obligatoire("CLE", en_developpement="locale") == "valeur"
    env.verifier()


def test_obligatoire_absent_sur_le_serveur_est_note():
    env = serveur(CLE="   ")
    assert env.obligatoire("CLE", en_developpement="locale") is None
    assert env.manquantes == ["CLE"]


def test_obligatoire_absent_en_developpement_prend_la_valeur_locale():
    env = developpement()
    assert env.obligatoire("CLE", en_developpement="locale") == "locale"
    env.verifier()


def test_verifier_nomme_toutes_les_variables_manquantes():
    env = serveur()
    env.obligatoire("PREMIERE", en_developpement="")
    env.obligatoire("SECONDE", en_developpement="")
    with pytest.raises(ImproperlyConfigured, match="PREMIERE, SECONDE"):
        env.verifier()


def test_les_variables_lues_sont_retenues():
    env = serveur(CLE="valeur")
    env.obligatoire("CLE", en_developpement="")
    assert env.lues == {"DJANGO_DEBUG", "CLE"}


def test_liste_separee_par_des_virgules():
    env = serveur(HOTES=" motsencommun.fr, www.motsencommun.fr ,, ")
    assert env.liste("HOTES", en_developpement=[]) == [
        "motsencommun.fr",
        "www.motsencommun.fr",
    ]


def test_liste_absente():
    assert developpement().liste("HOTES", en_developpement=["localhost"]) == [
        "localhost"
    ]
    env = serveur()
    assert env.liste("HOTES", en_developpement=["localhost"]) == []
    assert env.manquantes == ["HOTES"]


def test_dossier_absolu(tmp_path):
    assert (
        serveur(DOSSIER=str(tmp_path)).dossier("DOSSIER", en_developpement=None)
        == tmp_path
    )


def test_dossier_relatif_refuse():
    with pytest.raises(ImproperlyConfigured, match="chemin absolu"):
        serveur(DOSSIER="donnees").dossier("DOSSIER", en_developpement=None)


def test_dossier_en_developpement(tmp_path):
    assert developpement().dossier("DOSSIER", en_developpement=tmp_path) == Path(
        tmp_path
    )


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [
        ("gestion-x7k2", "gestion-x7k2/"),
        ("/gestion-x7k2/", "gestion-x7k2/"),
        ("coulisses/x7_k2", "coulisses/x7_k2/"),
    ],
)
def test_chemin_admin_normalise(valeur, attendu):
    assert serveur(CHEMIN_ADMIN=valeur).chemin_admin("CHEMIN_ADMIN") == attendu


@pytest.mark.parametrize(
    "valeur",
    ["/", "gestion x", "a//b", "gestion/../x", "gestion?x=1", "<str:x>", "géstion"],
)
def test_chemin_admin_invalide_refuse(valeur):
    with pytest.raises(ImproperlyConfigured, match="CHEMIN_ADMIN vaut"):
        serveur(CHEMIN_ADMIN=valeur).chemin_admin("CHEMIN_ADMIN")


@pytest.mark.parametrize("valeur", ["admin", "/admin/", "Admin/"])
def test_chemin_admin_par_defaut_refuse_sur_le_serveur(valeur):
    with pytest.raises(ImproperlyConfigured, match="difficile à deviner"):
        serveur(CHEMIN_ADMIN=valeur).chemin_admin("CHEMIN_ADMIN")


def test_chemin_admin_en_developpement():
    assert developpement().chemin_admin("CHEMIN_ADMIN") == "admin/"
    assert developpement(CHEMIN_ADMIN="admin").chemin_admin("CHEMIN_ADMIN") == "admin/"


def test_chemin_admin_absent_sur_le_serveur_est_note():
    env = serveur()
    assert env.chemin_admin("CHEMIN_ADMIN") is None
    assert env.manquantes == ["CHEMIN_ADMIN"]

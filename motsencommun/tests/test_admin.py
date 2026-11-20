"""L'administration est servie au chemin choisi dans la configuration, et nulle part ailleurs."""

import importlib

from django.conf import settings
from django.test import override_settings
from django.urls import clear_url_caches, reverse


def recharger_les_adresses():
    """Reconstruit les adresses du site à partir des réglages en cours."""
    clear_url_caches()
    importlib.reload(importlib.import_module(settings.ROOT_URLCONF))


def test_l_administration_est_au_chemin_configure(client):
    assert settings.CHEMIN_ADMIN == "gestion-tests/"
    assert reverse("admin:index") == "/gestion-tests/"
    assert client.get("/gestion-tests/login/").status_code == 200


def test_l_adresse_par_defaut_n_existe_pas(client):
    assert client.get("/admin/").status_code == 404
    assert client.get("/admin/login/").status_code == 404


def test_changer_le_reglage_deplace_l_administration(client):
    try:
        with override_settings(CHEMIN_ADMIN="ailleurs-9q2z/"):
            recharger_les_adresses()
            assert reverse("admin:index") == "/ailleurs-9q2z/"
            assert client.get("/ailleurs-9q2z/login/").status_code == 200
            assert client.get("/gestion-tests/login/").status_code == 404
    finally:
        recharger_les_adresses()
    assert reverse("admin:index") == "/gestion-tests/"

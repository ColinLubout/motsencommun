"""La commande qui active la double authentification d'un compte."""

import io

import pytest
from django.core.management import CommandError, call_command
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from lexique.management.commands.activer_double_authentification import Command

pytestmark = pytest.mark.django_db


def repondre_avec(monkeypatch, code=None):
    """La personne tape le code de son application (ou un code donné)."""

    def lire_code(commande):
        if code is not None:
            return code
        appareil = TOTPDevice.objects.get(confirmed=False)
        return f"{totp(appareil.bin_key):06d}"

    monkeypatch.setattr(Command, "lire_code", lire_code)


def activer(*arguments):
    sortie = io.StringIO()
    call_command("activer_double_authentification", *arguments, stdout=sortie)
    return sortie.getvalue()


def test_la_commande_installe_l_application_et_dix_codes(monkeypatch, proprietaire):
    repondre_avec(monkeypatch)
    sortie = activer("proprietaire")
    appareil = TOTPDevice.objects.get(user=proprietaire)
    assert appareil.confirmed
    codes = list(
        StaticDevice.objects.get(user=proprietaire).token_set.values_list(
            "token", flat=True
        )
    )
    assert len(codes) == 10
    assert all(code in sortie for code in codes)
    assert "Scannez ce QR code" in sortie
    assert "Double authentification activée" in sortie


def test_un_mauvais_code_n_enregistre_rien(monkeypatch, proprietaire):
    repondre_avec(monkeypatch, code="000000")
    with pytest.raises(CommandError, match="rien n'a été enregistré"):
        activer("proprietaire")
    assert not TOTPDevice.objects.exists()
    assert not StaticDevice.objects.exists()


def test_la_commande_ne_remplace_qu_a_la_demande(monkeypatch, proprietaire):
    repondre_avec(monkeypatch)
    activer("proprietaire")
    ancien = TOTPDevice.objects.get(user=proprietaire).pk
    with pytest.raises(CommandError, match="--remplacer"):
        activer("proprietaire")
    activer("proprietaire", "--remplacer")
    assert TOTPDevice.objects.get(user=proprietaire).pk != ancien
    assert StaticDevice.objects.filter(user=proprietaire).count() == 1


def test_un_compte_inconnu_est_signale():
    with pytest.raises(CommandError, match="Aucun compte"):
        activer("personne")

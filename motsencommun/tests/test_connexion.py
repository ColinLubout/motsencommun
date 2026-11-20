"""Connexion à l'administration : double authentification, mots de passe, freinage, sessions."""

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import (
    password_validators_help_texts,
    validate_password,
)
from django.core.cache import cache
from django.core.cache.backends import locmem
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from lexique.tests.conftest import MOT_DE_PASSE, creer_compte
from motsencommun import connexion

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def cache_vide():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def superutilisateur():
    return creer_compte(
        "chef", superutilisateur=True, relit=["fr"], mot_de_passe=MOT_DE_PASSE
    )


def code_de(appareil):
    return f"{totp(appareil.bin_key):06d}"


def se_connecter(
    client, nom, mot_de_passe=MOT_DE_PASSE, code="", adresse="203.0.113.7"
):
    return client.post(
        reverse("admin:login"),
        {"username": nom, "password": mot_de_passe, "otp_token": code},
        REMOTE_ADDR=adresse,
    )


def peut_ouvrir_l_administration(client):
    return client.get(reverse("admin:index")).status_code == 200


# --- Double authentification ----------------------------------------------------


def test_un_superutilisateur_sans_appareil_n_entre_pas(client, superutilisateur):
    """Critère d'acceptation : un superutilisateur connecté, sans appareil, n'ouvre pas l'admin."""
    client.force_login(superutilisateur)
    reponse = client.get(reverse("admin:index"))
    assert reponse.status_code == 302
    assert reverse("admin:login") in reponse.url
    reponse = se_connecter(Client(), "chef")
    assert "Saisissez votre code" in reponse.content.decode()


def test_un_superutilisateur_entre_avec_son_code(client, superutilisateur):
    appareil = TOTPDevice.objects.create(
        user=superutilisateur, name="Téléphone", confirmed=True
    )
    assert "Saisissez votre code" in se_connecter(client, "chef").content.decode()
    assert (
        "Code invalide" in se_connecter(client, "chef", code="000000").content.decode()
    )
    assert not peut_ouvrir_l_administration(client)
    # Juste après un code faux, django-otp fait patienter, même avec le bon code.
    reponse = se_connecter(client, "chef", code=code_de(appareil))
    assert "réessayez dans un instant" in reponse.content.decode()
    appareil.refresh_from_db()
    appareil.throttle_reset()  # le délai est passé
    assert se_connecter(client, "chef", code=code_de(appareil)).status_code == 302
    assert peut_ouvrir_l_administration(client)


def test_un_code_de_secours_sert_une_seule_fois(superutilisateur):
    TOTPDevice.objects.create(user=superutilisateur, name="Téléphone", confirmed=True)
    secours = StaticDevice.objects.create(
        user=superutilisateur, name="Codes de secours"
    )
    secours.token_set.create(token="secours1")
    premier = Client()
    assert se_connecter(premier, "chef", code="secours1").status_code == 302
    assert peut_ouvrir_l_administration(premier)
    assert (
        "Code invalide"
        in se_connecter(Client(), "chef", code="secours1").content.decode()
    )


def test_un_relecteur_avec_un_appareil_doit_donner_son_code(client):
    relectrice = creer_compte("relectrice", relecteur=True, mot_de_passe=MOT_DE_PASSE)
    appareil = TOTPDevice.objects.create(
        user=relectrice, name="Téléphone", confirmed=True
    )
    assert "Saisissez votre code" in se_connecter(client, "relectrice").content.decode()
    assert se_connecter(client, "relectrice", code=code_de(appareil)).status_code == 302
    assert peut_ouvrir_l_administration(client)


# --- Mots de passe --------------------------------------------------------------


def test_les_mots_de_passe_sont_haches_avec_argon2(superutilisateur):
    """Critère d'acceptation : les mots de passe sont stockés avec Argon2."""
    assert superutilisateur.password.startswith("argon2$")
    assert superutilisateur.check_password(MOT_DE_PASSE)


def test_un_mot_de_passe_de_15_caracteres_est_refuse():
    """Critère d'acceptation : 15 caractères sont refusés, 16 acceptés."""
    with pytest.raises(ValidationError, match="16 caractères"):
        validate_password("lampe cerise vo")  # 15 caractères
    validate_password("lampe cerise voy")  # 16 caractères


def test_pas_de_longueur_maximale_sous_128_caracteres():
    validate_password("tortue lampe cerise voyage " * 5)  # 135 caractères


def test_le_formulaire_conseille_une_phrase_de_passe():
    assert any("phrase de passe" in texte for texte in password_validators_help_texts())


# --- Freinage des essais ratés -------------------------------------------------


def test_dix_echecs_bloquent_le_compte_quinze_minutes(monkeypatch):
    """Critère d'acceptation : les connexions ratées à répétition sont freinées."""
    creer_compte("relectrice", relecteur=True, mot_de_passe=MOT_DE_PASSE)
    for numero in range(10):
        se_connecter(
            Client(),
            "relectrice",
            "mauvais mot de passe",
            adresse=f"198.51.100.{numero}",
        )
    # Même avec le bon mot de passe, et depuis une autre adresse : il faut attendre.
    reponse = se_connecter(Client(), "Relectrice", adresse="192.0.2.1")
    assert "Réessayez dans 15 minutes" in reponse.content.decode()

    debut = locmem.time.time()
    monkeypatch.setattr(locmem.time, "time", lambda: debut + 15 * 60 + 1)
    assert se_connecter(Client(), "relectrice", adresse="192.0.2.1").status_code == 302


def test_dix_echecs_bloquent_l_adresse():
    creer_compte("relectrice", relecteur=True, mot_de_passe=MOT_DE_PASSE)
    for numero in range(10):
        se_connecter(Client(), f"inconnu{numero}", "mauvais", adresse="198.51.100.9")
    assert (
        "Réessayez dans 15 minutes"
        in se_connecter(Client(), "relectrice", adresse="198.51.100.9").content.decode()
    )
    assert se_connecter(Client(), "relectrice", adresse="192.0.2.1").status_code == 302


def test_neuf_echecs_ne_bloquent_pas():
    creer_compte("relectrice", relecteur=True, mot_de_passe=MOT_DE_PASSE)
    for _essai in range(9):
        se_connecter(Client(), "relectrice", "mauvais")
    assert se_connecter(Client(), "relectrice").status_code == 302


def test_un_mauvais_code_compte_comme_un_echec(superutilisateur):
    TOTPDevice.objects.create(user=superutilisateur, name="Téléphone", confirmed=True)
    for numero in range(10):
        se_connecter(Client(), "chef", code="000000", adresse=f"198.51.100.{numero}")
    assert (
        "Réessayez dans 15 minutes"
        in se_connecter(Client(), "chef", adresse="192.0.2.1").content.decode()
    )


def test_aucune_adresse_ni_aucun_nom_n_est_garde_en_clair():
    creer_compte("relectrice", relecteur=True, mot_de_passe=MOT_DE_PASSE)
    se_connecter(Client(), "relectrice", "mauvais", adresse="198.51.100.77")
    cles = " ".join(str(cle) for cle in locmem._caches[""])
    assert cles
    assert "198.51.100.77" not in cles
    assert "relectrice" not in cles


def test_derriere_caddy_l_adresse_est_la_derniere_transmise(rf):
    requete = rf.get("/", HTTP_X_FORWARDED_FOR="10.0.0.1, 203.0.113.5", REMOTE_ADDR="")
    assert connexion.adresse_du_client(requete) == "203.0.113.5"
    assert (
        connexion.adresse_du_client(rf.get("/", REMOTE_ADDR="192.0.2.8")) == "192.0.2.8"
    )


# --- Sessions ------------------------------------------------------------------


def test_les_sessions_durent_douze_heures(client):
    """Critère d'acceptation : les sessions de l'équipe expirent après 12 heures."""
    creer_compte("relectrice", relecteur=True, mot_de_passe=MOT_DE_PASSE)
    reponse = se_connecter(client, "relectrice")
    assert client.session.get_expiry_age() == 12 * 60 * 60
    cookie = reponse.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["max-age"] == 12 * 60 * 60
    assert cookie["secure"] is True
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"


def test_changer_de_mot_de_passe_deconnecte_les_autres_sessions():
    relectrice = creer_compte("relectrice", relecteur=True, mot_de_passe=MOT_DE_PASSE)
    ailleurs = Client()
    ailleurs.force_login(relectrice)
    assert peut_ouvrir_l_administration(ailleurs)
    relectrice = User.objects.get(pk=relectrice.pk)
    relectrice.set_password("un tout autre mot de passe assez long")
    relectrice.save()
    assert not peut_ouvrir_l_administration(ailleurs)

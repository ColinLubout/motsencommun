"""Traductions de l'interface : catalogue anglais complet, administration en français."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

CATALOGUE_ANGLAIS = Path(settings.BASE_DIR, "locale", "en", "LC_MESSAGES", "django.po")


def entrees_du_catalogue(chemin):
    """Les entrées d'un .po : (indicateurs, msgid, [msgstr…]), sans l'en-tête."""
    texte = chemin.read_text("utf-8")
    for bloc in re.split(r"\n\s*\n", texte):
        indicateurs = " ".join(re.findall(r"^#,(.*)$", bloc, re.MULTILINE))
        parties = {}
        cle = None
        for ligne in bloc.splitlines():
            if debut := re.match(
                r'^(msgid(?:_plural)?|msgstr(?:\[\d+\])?) "(.*)"$', ligne
            ):
                cle = debut.group(1)
                parties[cle] = debut.group(2)
            elif cle and (suite := re.match(r'^"(.*)"$', ligne)):
                parties[cle] += suite.group(1)
        if parties.get("msgid"):
            traductions = [v for k, v in parties.items() if k.startswith("msgstr")]
            yield indicateurs, parties["msgid"], traductions


def test_le_catalogue_anglais_est_complet():
    """L'interface existe en anglais : chaque texte a sa traduction, aucune n'est douteuse."""
    entrees = list(entrees_du_catalogue(CATALOGUE_ANGLAIS))
    assert len(entrees) > 250
    for indicateurs, msgid, traductions in entrees:
        assert "fuzzy" not in indicateurs, msgid
        assert traductions and all(traductions), f"pas de traduction pour « {msgid} »"


def test_les_parametres_sont_les_memes_dans_la_traduction():
    for _indicateurs, msgid, traductions in entrees_du_catalogue(CATALOGUE_ANGLAIS):
        attendus = set(re.findall(r"%\(\w+\)[sd]", msgid))
        for traduction in traductions:
            assert set(re.findall(r"%\(\w+\)[sd]", traduction)) == attendus, msgid


@pytest.fixture
def client_superutilisateur(client, django_user_model):
    compte = django_user_model.objects.create_superuser("chef", "chef@example.org")
    appareil = TOTPDevice.objects.create(user=compte, name="Téléphone", confirmed=True)
    client.force_login(compte)
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = appareil.persistent_id
    session.save()
    return client


def test_l_administration_reste_en_francais_meme_pour_un_navigateur_anglais(
    client_superutilisateur,
):
    """Décidé le 20 novembre 2026 : l'administration ne suit pas la langue du navigateur."""
    reponse = client_superutilisateur.get(
        reverse("admin:index"), HTTP_ACCEPT_LANGUAGE="en-GB,en;q=0.9"
    )
    contenu = reponse.content.decode()
    assert '<html lang="fr"' in contenu
    assert "Entrées" in contenu
    assert "Entries" not in contenu
    assert "Accept-Language" not in reponse.get("Vary", "")


def test_la_page_de_connexion_reste_en_francais(client, db):
    reponse = client.get(reverse("admin:login"), HTTP_ACCEPT_LANGUAGE="en")
    assert "Se connecter" in reponse.content.decode()

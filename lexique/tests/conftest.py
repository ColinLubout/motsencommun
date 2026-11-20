"""Comptes et contenus de test, partagés par les tests du lexique."""

import types

import pytest
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from lexique import models as m
from lexique.apps import NOM_DU_GROUPE_DES_RELECTEURS

MOT_DE_PASSE = "tortue lampe cerise voyage"


@pytest.fixture(autouse=True)
def cache_vide():
    cache.clear()
    yield
    cache.clear()


def creer_compte(
    nom, *, superutilisateur=False, relecteur=False, relit=(), mot_de_passe=None
):
    """Un compte, avec son profil. Sans mot de passe, il n'est pas haché (tests plus rapides)."""
    utilisateur = User(username=nom, email=f"{nom}@example.org")
    utilisateur.is_superuser = utilisateur.is_staff = superutilisateur
    if relecteur:
        utilisateur.is_staff = True
    if mot_de_passe:
        utilisateur.set_password(mot_de_passe)
    else:
        utilisateur.set_unusable_password()
    utilisateur.save()
    if relecteur:
        utilisateur.groups.add(Group.objects.get(name=NOM_DU_GROUPE_DES_RELECTEURS))
    utilisateur.contributeur.relit_langues = list(relit)
    utilisateur.contributeur.save()
    return utilisateur


@pytest.fixture
def proprietaire(db):
    return creer_compte("proprietaire", superutilisateur=True, relit=["fr"])


@pytest.fixture
def relecteur(db):
    return creer_compte("relecteur", relecteur=True, relit=["fr"])


@pytest.fixture
def tuteur(db):
    return creer_compte("tuteur", relecteur=True, relit=["fr", "en"])


@pytest.fixture
def import_initial(db):
    """Le compte système auquel les données de départ sont attribuées."""
    return creer_compte("import-initial")


def creer_entree(auteur, **champs):
    valeurs = {
        "vedette": "poser un lapin à qqn",
        "type_entree": "expression",
        "nature": "locution_verbale",
        "niveau": "B1",
        "registre": "familier",
        "frequence": "courante",
        "sens_b1": "Ne pas venir à un rendez-vous, sans prévenir.",
    }
    valeurs.update(champs)
    return m.Entree.objects.create(ajoute_par=auteur, **valeurs)


def creer_piege(entree, auteur, **champs):
    valeurs = {
        "type_piege": "sens_figure",
        "concerne": ["comprehension"],
        "gravite": "moyenne",
        "explication_b1": "Rien à voir avec les lapins : la personne n'est pas venue.",
    }
    valeurs.update(champs)
    return m.Piege.objects.create(entree=entree, ajoute_par=auteur, **valeurs)


def creer_exemple(
    entree, auteur, phrase=None, surlignage="m'a posé un lapin", **champs
):
    exemple = m.Exemple.objects.create(
        phrase=phrase or "Il m'a posé un lapin hier soir.",
        niveau=champs.pop("niveau", "B1"),
        ajoute_par=auteur,
        **champs,
    )
    m.ExempleEntree.objects.create(
        exemple=exemple, entree=entree, surlignage=surlignage
    )
    return exemple


#: Textes de test en ukrainien et en polonais (PRD, « Every alphabet ») : recherche,
#: tri, et plus tard surlignage et export.
SENS_UKRAINIEN = "Мій рідний край — Київ. Без мʼяса й хліба."
SENS_POLONAIS = "Łódź to miasto, a łąka jest zielona."
#: Des mots dans l'ordre de leur alphabet.
POLONAIS_DANS_L_ORDRE = [
    "az",
    "ąb",
    "cebula",
    "ćma",
    "lampa",
    "łąka",
    "oko",
    "ósmy",
    "sok",
    "śnieg",
    "zebra",
    "źle",
    "żaba",
]
UKRAINIEN_DANS_L_ORDRE = [
    "бук",
    "гора",
    "ґанок",
    "ефір",
    "єнот",
    "иній",
    "іній",
    "їжак",
    "йод",
    "кіт",
    "щука",
    "яблуко",
]
FRANCAIS_DANS_L_ORDRE = [
    "abri",
    "ancien",
    "ancienne",
    "cote",
    "côte",
    "école",
    "élève",
    "etre",
    "Être",
    "zèbre",
]


@pytest.fixture
def entree_multilingue(db, proprietaire):
    """Une entrée traduite en ukrainien et en polonais."""
    entree = creer_entree(proprietaire)
    for langue, sens in (("uk", SENS_UKRAINIEN), ("pl", SENS_POLONAIS)):
        m.EntreeTraduction.objects.create(
            entree=entree, langue=langue, sens=sens, ajoute_par=proprietaire
        )
    return entree


def rendre_public(*contenus, statut="relu"):
    """Donne un statut sans passer par les relectures : pour tester l'affichage seulement."""
    for contenu in contenus:
        type(contenu).objects.filter(pk=contenu.pk).update(statut=statut)
        contenu.statut = statut


@pytest.fixture
def site_public(db, proprietaire):
    """Un petit lexique public, avec à côté du contenu pas encore relu."""
    relations = m.Theme.objects.create(slug="relations", nom="Relations")
    temps = m.Theme.objects.create(slug="temps", nom="Temps et durée")
    lapin = creer_entree(proprietaire)
    lapin.themes.add(relations)
    piege = creer_piege(lapin, proprietaire)
    piege_cache = creer_piege(
        lapin,
        proprietaire,
        type_piege="faux_ami",
        explication_b1="Une explication pas encore relue.",
    )
    exemple = creer_exemple(lapin, proprietaire)
    exemple_cache = creer_exemple(
        lapin,
        proprietaire,
        phrase="Une phrase pas encore relue, avec un lapin.",
        surlignage="un lapin",
    )
    traduction = m.EntreeTraduction.objects.create(
        entree=lapin, langue="en", sens="to stand someone up", ajoute_par=proprietaire
    )
    lune = creer_entree(
        proprietaire,
        vedette="être dans la lune",
        niveau="A2",
        registre="courant",
        sens_b1="",
        sens_a2="Rêver, ne pas faire attention.",
    )
    lune.themes.add(temps)
    secrete = creer_entree(
        proprietaire, vedette="expression secrète", sens_b1="Pas encore relue."
    )
    m.LienEntree.objects.create(entree=lapin, cible=lune, type_lien="voir_aussi")
    m.LienEntree.objects.create(entree=lapin, cible=secrete, type_lien="voir_aussi")
    rendre_public(lapin, piege, exemple, traduction, lune)
    return types.SimpleNamespace(
        lapin=lapin,
        piege=piege,
        piege_cache=piege_cache,
        exemple=exemple,
        exemple_cache=exemple_cache,
        traduction=traduction,
        lune=lune,
        secrete=secrete,
        relations=relations,
        temps=temps,
    )


def relire(contenu, relecteur, decision="approuve", commentaire=""):
    return m.Relecture.objects.create(
        contenu=contenu, relecteur=relecteur, decision=decision, commentaire=commentaire
    )


def modifier(contenu, utilisateur, **champs):
    """Modifie un contenu comme le ferait cette personne (l'historique la retient)."""
    for nom, valeur in champs.items():
        setattr(contenu, nom, valeur)
    contenu._history_user = utilisateur
    contenu.save()
    return contenu


@pytest.fixture
def client_proprietaire(client, proprietaire):
    """Un navigateur connecté en superutilisateur, double authentification passée."""
    appareil = TOTPDevice.objects.create(
        user=proprietaire, name="Téléphone", confirmed=True
    )
    client.force_login(proprietaire)
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = appareil.persistent_id
    session.save()
    return client


@pytest.fixture
def client_relecteur(client, relecteur):
    client.force_login(relecteur)
    return client

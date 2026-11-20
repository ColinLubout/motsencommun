"""Comptes et contenus de test, partagés par les tests du lexique."""

import pytest
from django.contrib.auth.models import Group, User
from django.core.cache import cache

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
    """Un navigateur connecté en superutilisateur."""
    client.force_login(proprietaire)
    return client


@pytest.fixture
def client_relecteur(client, relecteur):
    client.force_login(relecteur)
    return client

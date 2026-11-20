"""Chaque modèle garde son historique, et l'administration le montre."""

import pytest
from django.apps import apps
from django.urls import reverse
from simple_history.models import HistoricalChanges

from lexique import models as m
from lexique.tests.conftest import (
    creer_entree,
    creer_exemple,
    creer_piege,
    modifier,
    relire,
)

pytestmark = pytest.mark.django_db

MODELES = [
    modele
    for modele in apps.get_app_config("lexique").get_models()
    if not issubclass(modele, HistoricalChanges) and not modele._meta.auto_created
]


def test_tous_les_modeles_sont_couverts():
    noms = {modele.__name__ for modele in MODELES}
    assert noms == {
        "Theme",
        "ThemeTraduction",
        "Entree",
        "LienEntree",
        "Piege",
        "Exemple",
        "ExempleEntree",
        "EntreeTraduction",
        "PiegeTraduction",
        "ExempleTraduction",
        "Contributeur",
        "Relecture",
    }


@pytest.mark.parametrize("modele", MODELES, ids=lambda modele: modele.__name__)
def test_chaque_modele_a_un_historique(modele):
    assert hasattr(modele, "history"), f"{modele.__name__} n'a pas d'historique"


def test_l_historique_retient_qui_a_modifie_quoi(proprietaire, import_initial):
    entree = creer_entree(import_initial)
    modifier(entree, proprietaire, sens_b1="Ne pas venir.")
    versions = list(entree.history.order_by("history_date"))
    assert [version.sens_b1 for version in versions] == [
        "Ne pas venir à un rendez-vous, sans prévenir.",
        "Ne pas venir.",
    ]
    assert versions[-1].history_user == proprietaire


def test_l_historique_retient_les_themes(import_initial):
    entree = creer_entree(import_initial)
    theme = m.Theme.objects.create(slug="relations", nom="Relations")
    entree.themes.add(theme)
    assert entree.history.latest().themes.count() == 1


@pytest.fixture
def un_de_chaque(import_initial, relecteur, tuteur):
    """Un enregistrement de chaque modèle."""
    entree = creer_entree(import_initial)
    autre = creer_entree(import_initial, vedette="manquer à qqn")
    piege = creer_piege(entree, import_initial)
    exemple = creer_exemple(entree, import_initial)
    theme = m.Theme.objects.create(slug="relations", nom="Relations")
    return {
        m.Entree: entree,
        m.Piege: piege,
        m.Exemple: exemple,
        m.ExempleEntree: exemple.liens_entrees.get(),
        m.Theme: theme,
        m.ThemeTraduction: m.ThemeTraduction.objects.create(
            theme=theme, langue="en", nom="Relationships"
        ),
        m.LienEntree: m.LienEntree.objects.create(
            entree=entree, cible=autre, type_lien="voir_aussi"
        ),
        m.EntreeTraduction: m.EntreeTraduction.objects.create(
            entree=entree,
            langue="en",
            sens="to stand someone up",
            ajoute_par=import_initial,
        ),
        m.PiegeTraduction: m.PiegeTraduction.objects.create(
            piege=piege,
            langue="en",
            explication="Nothing to do with rabbits.",
            ajoute_par=import_initial,
        ),
        m.ExempleTraduction: m.ExempleTraduction.objects.create(
            exemple=exemple,
            langue="en",
            traduction="He stood me up.",
            ajoute_par=import_initial,
        ),
        m.Contributeur: import_initial.contributeur,
        m.Relecture: relire(entree, relecteur),
    }


@pytest.mark.parametrize("modele", MODELES, ids=lambda modele: modele.__name__)
def test_l_administration_montre_l_historique(
    client_proprietaire, un_de_chaque, modele
):
    """Critère d'acceptation : l'administration montre l'historique de chaque enregistrement."""
    objet = un_de_chaque[modele]
    adresse = reverse(
        f"admin:lexique_{modele._meta.model_name}_history", args=[objet.pk]
    )
    reponse = client_proprietaire.get(adresse)
    assert reponse.status_code == 200
    assert objet.history.count() >= 1

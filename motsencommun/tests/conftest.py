"""Outils partagés par les tests du projet."""

import re
import runpy
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[2]
REGLAGES = RACINE / "motsencommun" / "settings.py"
ENV_EXEMPLE = RACINE / "deploiement" / "env.exemple"


def lire_variables_documentees():
    """Noms des variables d'environnement décrites dans deploiement/env.exemple."""
    texte = ENV_EXEMPLE.read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Z][A-Z0-9_]*)=", texte, flags=re.MULTILINE))


@pytest.fixture
def variables_documentees():
    """Noms des variables d'environnement décrites dans deploiement/env.exemple."""
    return lire_variables_documentees()


@pytest.fixture
def charger_reglages(monkeypatch):
    """Exécute settings.py avec les seules variables d'environnement données.

    Toutes les variables documentées sont d'abord retirées, puis celles passées
    en argument sont posées. Le fichier est exécuté à part : les réglages du
    reste de la suite de tests ne changent pas. Renvoie les variables globales
    du module, par exemple ``reglages["DEBUG"]`` ou ``reglages["env"]``.
    """

    def charger(**variables):
        for nom in lire_variables_documentees():
            monkeypatch.delenv(nom, raising=False)
        for nom, valeur in variables.items():
            monkeypatch.setenv(nom, valeur)
        return runpy.run_path(str(REGLAGES), run_name="reglages_isoles")

    return charger

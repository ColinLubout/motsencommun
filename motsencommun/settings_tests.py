"""Réglages de la suite de tests.

Les tests tournent avec les réglages de production (``DJANGO_DEBUG`` à 0) :
ce module fournit seulement les variables que la production exige, avec des
valeurs qui ne servent qu'aux tests, puis charge les réglages normaux.
"""

import os
import tempfile
from pathlib import Path

VARIABLES_DES_TESTS = {
    "DJANGO_DEBUG": "0",
    "DJANGO_SECRET_KEY": "cle-reservee-aux-tests-et-sans-valeur-ailleurs-0123456789abcdef",
    "DJANGO_ALLOWED_HOSTS": "testserver",
    "CHEMIN_ADMIN": "gestion-tests/",
    # Les tests utilisent une base en mémoire : rien n'est écrit dans ce dossier.
    "DOSSIER_DONNEES": str(Path(tempfile.gettempdir()) / "motsencommun-tests"),
}
os.environ.update(VARIABLES_DES_TESTS)

from motsencommun.settings import *

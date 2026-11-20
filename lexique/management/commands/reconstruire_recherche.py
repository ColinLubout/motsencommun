"""Recalcule les champs de recherche et les clés de tri des entrées et de leurs traductions.

À lancer après une mise à jour d'ICU sur le serveur (les clés de tri en
dépendent) ou après un changement des règles de lexique/recherche.py. Ne touche
ni au texte, ni au statut, ni à l'historique.
"""

import icu
from django.core.management.base import BaseCommand
from django.db import transaction

from lexique.models import Entree, EntreeTraduction
from lexique.recherche import reconstruire


class Command(BaseCommand):
    help = (
        "Recalcule les champs de recherche et les clés de tri (après une mise à jour "
        "d'ICU, par exemple). Ne touche ni au texte, ni au statut, ni à l'historique."
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            entrees, traductions = reconstruire(Entree, EntreeTraduction)
        self.stdout.write(
            f"Recherche reconstruite avec ICU {icu.ICU_VERSION} : "
            f"{entrees} {'entrée mise' if entrees < 2 else 'entrées mises'} à jour, "
            f"{traductions} "
            f"{'traduction mise' if traductions < 2 else 'traductions mises'} à jour."
        )

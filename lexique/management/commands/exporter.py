"""Écrit les fichiers à télécharger : JSON, CSV et dictionnaire de données.

Sur le serveur, un minuteur systemd la lance chaque nuit. Le premier du mois
(à l'heure de Paris), elle garde aussi une copie datée dans
instantanes/AAAA-MM/, qui n'est jamais remplacée.

    uv run python manage.py exporter
    uv run python manage.py exporter --instantane   # l'instantané du mois, tout de suite
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from lexique import exportation


class Command(BaseCommand):
    help = (
        "Écrit les fichiers à télécharger (contenu relu seulement) ; le premier du "
        "mois, garde aussi leur instantané daté."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--instantane",
            action="store_true",
            help="Garde l'instantané du mois même si ce n'est pas le premier.",
        )

    def handle(self, *args, instantane=False, **options):
        maintenant = timezone.now()
        nombre = exportation.exporter(maintenant)
        dossier = exportation.dossier_des_telechargements()
        self.stdout.write(
            self.style.SUCCESS(f"{nombre} entrée(s) exportée(s) dans {dossier}.")
        )
        aujourd_hui = timezone.localdate(maintenant)
        if instantane or aujourd_hui.day == 1:
            mois = aujourd_hui.strftime("%Y-%m")
            if exportation.enregistrer_instantane(mois):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Instantané du mois gardé : {exportation.DOSSIER_INSTANTANES}/{mois}/."
                    )
                )
            else:
                self.stdout.write(
                    f"L'instantané {mois} existe déjà : il reste tel quel."
                )

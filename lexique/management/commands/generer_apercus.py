"""Remet les images d'aperçu en accord avec les entrées.

Chaque entrée relue reçoit son image (si elle manque ou si son texte a
changé) ; les images des autres entrées, et celles d'entrées supprimées, sont
effacées. D'ordinaire, l'enregistrement d'une entrée s'en charge déjà : cette
commande sert après une restauration, une modification en masse, ou un
changement de la mise en page des images.

    uv run python manage.py generer_apercus
"""

from django.core.management.base import BaseCommand

from lexique import affichage as a
from lexique import apercus
from lexique.models import Entree


class Command(BaseCommand):
    help = (
        "Dessine l'image d'aperçu de chaque entrée relue et efface celles "
        "des entrées qui ne sont pas publiques."
    )

    def handle(self, *args, **options):
        slugs = set()
        publiques = 0
        for entree in Entree.objects.all():
            apercus.mettre_a_jour(entree)
            slugs.add(entree.slug)
            publiques += a.est_public(entree)
        orphelines = 0
        if apercus.dossier().exists():
            for fichier in apercus.dossier().glob("*.png"):
                if fichier.name.split(".", 1)[0] not in slugs:
                    fichier.unlink()
                    orphelines += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"{publiques} entrées relues ont leur image d'aperçu ; "
                f"{orphelines} image(s) d'entrées supprimées effacée(s)."
            )
        )

"""Importe les données initiales, rédigées par une IA, pour les essais seulement.

Exemple : ``python manage.py importer_donnees_initiales donnees/import/donnees-initiales.zip``

Tout arrive en brouillon, marqué « généré par IA » et attribué au compte système
import-initial. Le site en ligne est déployé à partir d'une base vide, sans
lancer cette commande. Voir lexique/import_initial.py.
"""

from django.core.management.base import BaseCommand, CommandError

from lexique.import_initial import NOM_DU_COMPTE, ErreurDImport, importer

#: Entrées déjà présentes nommées dans le compte rendu, au plus.
ENTREES_NOMMEES = 10


def nombre(n, singulier, pluriel):
    """« 0 exemple », « 1 exemple », « 2 exemples » : le singulier jusqu'à 1."""
    return f"{n} {singulier if n < 2 else pluriel}"


class Command(BaseCommand):
    help = (
        "Importe les données initiales (73 entrées rédigées par une IA, pour les essais "
        "seulement) en brouillon, marquées « généré par IA ». Relancer ne crée aucun "
        "doublon."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "chemin",
            help="L'archive donnees-initiales.zip, ou le dossier qui en est extrait.",
        )

    def handle(self, *args, chemin, **options):
        try:
            bilan = importer(chemin)
        except ErreurDImport as erreur:
            raise CommandError(f"{erreur} Rien n'a été importé.") from erreur

        if bilan.rien_de_nouveau:
            self.stdout.write("Rien de nouveau : ces données sont déjà importées.")
        else:
            crees = bilan.crees
            traductions = (
                crees["EntreeTraduction"]
                + crees["PiegeTraduction"]
                + crees["ExempleTraduction"]
            )
            self.stdout.write(
                self.style.SUCCESS(f"Données initiales importées depuis {chemin} :")
            )
            self.stdout.write(
                f"  {nombre(crees['Entree'], 'entrée', 'entrées')}, "
                f"{nombre(crees['Piege'], 'piège', 'pièges')}, "
                f"{nombre(crees['Exemple'], 'exemple', 'exemples')} "
                f"({nombre(crees['ExempleEntree'], 'rattachement', 'rattachements')} "
                "à des entrées),\n"
                f"  {nombre(crees['LienEntree'], 'lien', 'liens')} entre entrées, "
                f"{nombre(crees['Theme'], 'thème', 'thèmes')}, "
                f"{nombre(traductions, 'traduction anglaise', 'traductions anglaises')}."
            )
            self.stdout.write(
                "Tout est en brouillon, marqué « généré par IA » et attribué au compte "
                f"{NOM_DU_COMPTE}."
            )

        presentes = bilan.entrees_deja_presentes
        if presentes:
            noms = ", ".join(presentes[:ENTREES_NOMMEES])
            if len(presentes) > ENTREES_NOMMEES:
                noms += "…"
            if len(presentes) == 1:
                message = "1 entrée existait déjà et est restée telle quelle"
            else:
                message = (
                    f"{len(presentes)} entrées existaient déjà et sont restées telles "
                    "quelles"
                )
            self.stdout.write(f"{message} : {noms}")

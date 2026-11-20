"""Configuration de l'application lexique."""

from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate, post_save
from django.utils.translation import gettext_lazy as _

#: Le groupe des relecteurs et relectrices : voir le contenu et le relire, rien d'autre.
NOM_DU_GROUPE_DES_RELECTEURS = "Relecteurs"

#: Ce que ce groupe peut faire. Ni comptes, ni groupes, ni appareils de double
#: authentification, ni profils de contributeurs : seulement le contenu et ses relectures.
PERMISSIONS_DES_RELECTEURS = [
    "view_entree",
    "view_piege",
    "view_exemple",
    "view_exempleentree",
    "view_lienentree",
    "view_theme",
    "view_themetraduction",
    "view_entreetraduction",
    "view_piegetraduction",
    "view_exempletraduction",
    "view_relecture",
    "add_relecture",
]


def preparer_groupe_des_relecteurs(sender, using="default", **kwargs):
    """Crée le groupe des relecteurs et lui donne exactement ses permissions."""
    from django.contrib.auth.models import Group, Permission

    groupe, _cree = Group.objects.using(using).get_or_create(
        name=NOM_DU_GROUPE_DES_RELECTEURS
    )
    permissions = Permission.objects.using(using).filter(
        content_type__app_label="lexique", codename__in=PERMISSIONS_DES_RELECTEURS
    )
    groupe.permissions.set(permissions)


def creer_profil_de_contributeur(sender, instance, created, raw=False, **kwargs):
    """Chaque compte reçoit un profil de contributeur, crédité sous son nom d'utilisateur."""
    from lexique.models import Contributeur

    if created and not raw:
        Contributeur.objects.get_or_create(
            utilisateur=instance, defaults={"nom_affiche": instance.get_username()}
        )


class LexiqueConfig(AppConfig):
    """Les entrées, leurs pièges, leurs exemples et leurs traductions."""

    name = "lexique"
    verbose_name = _("Lexique")

    def ready(self):
        post_migrate.connect(preparer_groupe_des_relecteurs, sender=self)
        post_save.connect(creer_profil_de_contributeur, sender=settings.AUTH_USER_MODEL)

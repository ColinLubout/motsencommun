"""Ce que chaque page connaît : sa langue, le niveau du lecteur, les autres langues du site."""

from django.conf import settings
from django.urls import translate_url
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from lexique import affichage as a
from lexique import reperes
from lexique import vocabulaire as v

#: Paramètres que le formulaire « Mon niveau » ne recopie pas.
PARAMETRES_NON_CONSERVES = {"mon_niveau", "page"}


def site(request):
    langue = get_language()
    chemin = request.get_full_path()
    return {
        # Pour les moteurs de recherche et les aperçus de liens ; une fiche les remplace.
        **reperes.reperes_de_la_page(request),
        "description_du_site": _(
            "Les expressions françaises qui ne veulent pas dire ce que disent leurs mots, "
            "expliquées par celles et ceux qui apprennent et parlent le français."
        ),
        "langue": langue,
        "direction_langue": a.direction(langue),
        "mon_niveau": a.niveau_valide(request.GET.get("mon_niveau")),
        "niveaux": v.NIVEAUX,
        "langues_du_site": [
            {
                "code": code,
                "nom": nom,
                "adresse": translate_url(chemin, code),
                "active": code == langue,
            }
            for code, nom in settings.LANGUAGES
        ],
        "parametres_conserves": [
            (cle, valeur)
            for cle, valeur in request.GET.items()
            if cle not in PARAMETRES_NON_CONSERVES
        ],
    }

"""Repères pour les moteurs de recherche : adresse canonique, langues, plan du site.

Règles du PRD (« Findability ») :

- une fiche déclare une version dans une autre langue (``hreflang``) seulement
  pour les langues où l'entrée a une traduction relue ; dans les autres
  langues, son adresse canonique est la version française, pour que les
  moteurs ne voient pas de copies presque identiques ;
- les autres pages (accueil, listes, téléchargement, à propos) sont l'interface
  du site, traduite entièrement : chaque langue est sa propre version ;
- ``?mon_niveau=`` ne fait jamais partie de l'adresse canonique : il choisit
  seulement la version des explications ;
- le plan du site liste les adresses canoniques des pages publiques, et
  seulement des entrées relues.
"""

from django.conf import settings
from django.urls import reverse, translate_url
from django.utils import translation

from lexique import affichage as a
from lexique import models as m
from lexique import vocabulaire as v

#: Ce qui ne fait jamais partie de l'adresse canonique d'une page.
PARAMETRES_SANS_EFFET_SUR_LE_CONTENU = {"mon_niveau"}


def langues_du_site():
    return [code for code, _nom in settings.LANGUAGES]


def chemin_canonique(request):
    """Le chemin de la page, sans les paramètres qui ne changent pas son contenu."""
    parametres = request.GET.copy()
    for cle in PARAMETRES_SANS_EFFET_SUR_LE_CONTENU:
        parametres.pop(cle, None)
    requete = parametres.urlencode()
    return f"{request.path}?{requete}" if requete else request.path


def alternatives(request, chemin, langues):
    """Les versions de la page dans ``langues`` (et « x-default », le français), absolues."""
    if len(langues) < 2:
        return []
    versions = [
        {
            "code": code,
            "adresse": request.build_absolute_uri(translate_url(chemin, code)),
        }
        for code in langues
    ]
    versions.append(
        {
            "code": "x-default",
            "adresse": request.build_absolute_uri(
                translate_url(chemin, settings.LANGUAGE_CODE)
            ),
        }
    )
    return versions


def reperes_de_la_page(request):
    """Adresse canonique et versions dans les autres langues d'une page de l'interface."""
    chemin = chemin_canonique(request)
    return {
        "adresse_canonique": request.build_absolute_uri(chemin),
        "langues_alternatives": alternatives(request, chemin, langues_du_site()),
    }


def langues_traduites(entree):
    """Les langues du site où l'entrée a une traduction relue, français compris."""
    traduites = set(
        a.publics(entree.traductions.all()).values_list("langue", flat=True)
    )
    return [
        code
        for code in langues_du_site()
        if code == settings.LANGUAGE_CODE or code in traduites
    ]


def reperes_de_la_fiche(request, entree):
    """Pour une fiche : canonique en français si la langue de la page n'a pas de traduction."""
    langues = langues_traduites(entree)
    chemin = chemin_canonique(request)
    langue = translation.get_language()
    canonique = (
        chemin if langue in langues else translate_url(chemin, settings.LANGUAGE_CODE)
    )
    return {
        "adresse_canonique": request.build_absolute_uri(canonique),
        "langues_alternatives": alternatives(request, chemin, langues),
    }


# --- Plan du site -------------------------------------------------------------


def pages_de_l_interface():
    """Les pages publiques hors fiches, dans la langue active : accueil, listes, raccourcis…"""
    entrees = a.publics(m.Entree.objects.all())
    niveaux = set(entrees.values_list("niveau", flat=True))
    types = set(
        a.publics(m.Piege.objects.filter(entree__in=entrees))
        .values_list("type_piege", flat=True)
        .distinct()
    )
    themes = (
        m.Theme.objects.filter(entrees__in=entrees)
        .distinct()
        .values_list("slug", flat=True)
    )
    adresses = [
        reverse("lexique:accueil"),
        reverse("lexique:liste"),
        reverse("lexique:telecharger"),
        reverse("lexique:a_propos"),
    ]
    adresses += [
        reverse("lexique:par_niveau", args=[niveau.lower()])
        for niveau in v.NIVEAUX
        if niveau in niveaux
    ]
    adresses += [
        reverse("lexique:par_type", args=[code.replace("_", "-")])
        for code in v.TypePiege.values
        if code in types
    ]
    adresses += [reverse("lexique:par_theme", args=[slug]) for slug in sorted(themes)]
    return adresses


def adresses_du_plan(request):
    """Chaque adresse canonique publique : (adresse absolue, date de modification ou None)."""
    entrees = a.publics(m.Entree.objects.all()).order_by("slug")
    traduites = {}
    for entree, langue in a.publics(
        m.EntreeTraduction.objects.filter(entree__in=entrees)
    ).values_list("entree", "langue"):
        traduites.setdefault(entree, set()).add(langue)
    adresses = []
    for langue in langues_du_site():
        with translation.override(langue):
            adresses += [(chemin, None) for chemin in pages_de_l_interface()]
            for entree in entrees:
                if langue == settings.LANGUAGE_CODE or langue in traduites.get(
                    entree.pk, ()
                ):
                    adresses.append(
                        (
                            reverse("lexique:fiche", args=[entree.slug]),
                            entree.modifie_le,
                        )
                    )
    return [(request.build_absolute_uri(chemin), date) for chemin, date in adresses]

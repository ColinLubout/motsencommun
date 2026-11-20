"""Ce que voient les lecteurs : le contenu relu seulement, au niveau qu'ils ont choisi.

Règles d'affichage du PRD :

- seul le contenu « relu » ou « validé » est public ; le reste n'apparaît
  nulle part et son adresse répond 404 aux visiteurs ;
- connectés, le propriétaire et les relecteurs voient aussi le reste sur la
  fiche, signalé « Pas encore relu », pour relire ce que verront les lecteurs ;
- chaque sens et chaque explication s'affiche dans la version la plus haute
  au niveau du lecteur ou en dessous, sinon dans la plus basse qui existe.
"""

from django.conf import settings
from django.contrib import admin
from django.utils.translation import get_language_info

from lexique import vocabulaire as v

#: Ce que même l'aperçu des relecteurs ne montre pas.
STATUTS_ECARTES = [v.Statut.REFUSE, v.Statut.RETIRE]


def publics(contenus):
    """Le contenu relu ou validé seulement."""
    return contenus.filter(statut__in=v.STATUTS_PUBLICS)


def visibles(contenus, apercu):
    """Le contenu à montrer : relu pour les visiteurs, tout sauf refusé ou retiré en aperçu."""
    if apercu:
        return contenus.exclude(statut__in=STATUTS_ECARTES)
    return publics(contenus)


def est_public(contenu):
    return contenu.statut in v.STATUTS_PUBLICS


def voit_les_brouillons(request):
    """Le propriétaire ou un relecteur, connecté à l'administration.

    Sans cookie de session, la session n'est pas lue : la page d'un visiteur ne
    dépend que de son adresse (ni cookie, ni « Vary: Cookie »).
    """
    if settings.SESSION_COOKIE_NAME not in request.COOKIES:
        return False
    return admin.site.has_permission(request) and request.user.has_perm(
        "lexique.view_entree"
    )


def niveau_valide(valeur):
    """Le code de niveau (« B1 ») si ``valeur`` en est un, sans tenir compte de la casse."""
    code = (valeur or "").strip().upper()
    return code if code in v.NIVEAUX else None


def version_au_niveau(versions, niveau):
    """La version à afficher parmi ``versions`` ({"B1": "…"}, versions remplies seulement).

    La plus haute au niveau ``niveau`` ou en dessous ; s'il n'y en a pas, la plus
    basse qui existe. Renvoie (niveau de la version, texte), ou (None, "").
    """
    if not versions:
        return None, ""
    remplis = [n for n in v.NIVEAUX if n in versions]
    rang = v.NIVEAUX.index(niveau) if niveau in v.NIVEAUX else len(v.NIVEAUX) - 1
    en_dessous = [n for n in remplis if v.NIVEAUX.index(n) <= rang]
    choisi = en_dessous[-1] if en_dessous else remplis[0]
    return choisi, versions[choisi]


def decouper_surlignage(phrase, surlignage):
    """(avant, mots surlignés, après) : le gabarit entoure les mots de <mark>, texte échappé."""
    debut = phrase.find(surlignage) if surlignage else -1
    if debut < 0:
        return phrase, "", ""
    fin = debut + len(surlignage)
    return phrase[:debut], phrase[debut:fin], phrase[fin:]


def direction(langue):
    """« rtl » pour une langue écrite de droite à gauche, sinon « ltr »."""
    try:
        return "rtl" if get_language_info(langue)["bidi"] else "ltr"
    except KeyError:
        return "ltr"


def nom_du_theme(theme, langue):
    """(nom, langue du nom) : la traduction du thème dans ``langue``, sinon le nom français."""
    for traduction in theme.traductions.all():
        if traduction.langue == langue:
            return traduction.nom, langue
    return theme.nom, "fr"

"""Balises des gabarits publics : liens qui gardent le niveau du lecteur, pages, direction."""

from urllib.parse import urlencode

from django import template

from lexique import affichage as a

register = template.Library()


@register.simple_tag(takes_context=True)
def avec_niveau(context, adresse):
    """L'adresse, avec « mon_niveau » si le lecteur en a choisi un : il le garde de page en page."""
    niveau = context.get("mon_niveau")
    if not niveau:
        return adresse
    separateur = "&" if "?" in adresse else "?"
    return f"{adresse}{separateur}{urlencode({'mon_niveau': niveau})}"


@register.simple_tag(takes_context=True)
def adresse_de_la_page(context, numero):
    """L'adresse actuelle, à la page ``numero`` : filtres, requête et niveau gardés."""
    parametres = context["request"].GET.copy()
    parametres["page"] = numero
    return f"?{parametres.urlencode()}"


@register.filter
def direction(langue):
    """« rtl » ou « ltr », pour l'attribut ``dir`` d'un texte dans ``langue``."""
    return a.direction(langue)


@register.filter
def slug_du_type(code):
    """« faux_ami » → « faux-ami »."""
    return code.replace("_", "-")

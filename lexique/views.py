"""Pages publiques : accueil, liste et raccourcis, fiche, recherche, téléchargement, à propos.

Aucune de ces pages ne pose de cookie ni ne lit la session d'un visiteur
(voir ``affichage.voit_les_brouillons``), et aucune ne contient de formulaire
protégé par CSRF : tout passe par des liens et des formulaires GET.
"""

from urllib.parse import urlencode

from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import get_language, gettext_lazy
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_exempt

from lexique import affichage as a
from lexique import apercus, dictionnaire, exportation, reperes
from lexique import models as m
from lexique import recherche as r
from lexique import vocabulaire as v


def mon_niveau(request):
    """Le niveau choisi par le lecteur (« ?mon_niveau=A2 »), ou None."""
    return a.niveau_valide(request.GET.get("mon_niveau"))


def slug_du_type(code):
    """« faux_ami » → « faux-ami », pour les adresses des raccourcis."""
    return code.replace("_", "-")


def entrees_publiques():
    return a.publics(m.Entree.objects.all())


def resumes(entrees, niveau):
    """Chaque entrée d'une liste, avec son sens au niveau du lecteur, sinon au sien."""
    return [
        {
            "entree": entree,
            "niveau_du_sens": niveau_affiche,
            "sens": sens,
        }
        for entree in entrees
        for niveau_affiche, sens in [
            a.version_au_niveau(entree.sens(), niveau or entree.niveau)
        ]
    ]


def themes_publics(langue):
    """Les thèmes qui ont au moins une entrée publique, triés selon la langue de l'interface."""
    themes = (
        m.Theme.objects.filter(entrees__statut__in=v.STATUTS_PUBLICS)
        .distinct()
        .prefetch_related("traductions")
    )
    return [
        {"theme": theme, "nom": nom, "langue_du_nom": langue_du_nom}
        for theme in r.trier(themes, langue, cle=lambda t: a.nom_du_theme(t, langue)[0])
        for nom, langue_du_nom in [a.nom_du_theme(theme, langue)]
    ]


def types_publics():
    """Les types de pièges présents dans le contenu public, dans l'ordre du vocabulaire."""
    presents = set(
        a.publics(m.Piege.objects.filter(entree__statut__in=v.STATUTS_PUBLICS))
        .values_list("type_piege", flat=True)
        .distinct()
    )
    return [
        {"code": code, "libelle": libelle, "slug": slug_du_type(code)}
        for code, libelle in v.TypePiege.choices
        if code in presents
    ]


# --- Accueil ------------------------------------------------------------------


def accueil(request):
    langue = get_language()
    recentes = entrees_publiques().order_by("-cree_le", "-pk")[
        : settings.ENTREES_RECENTES
    ]
    return render(
        request,
        "lexique/accueil.html",
        {
            "themes": themes_publics(langue),
            "types": types_publics(),
            "recentes": resumes(recentes, mon_niveau(request)),
        },
    )


# --- Liste et raccourcis ------------------------------------------------------


def filtres_demandes(request, imposes=None):
    """Les filtres de l'adresse qui sont valides ; un raccourci impose le sien."""
    demande = request.GET
    type_piege = demande.get("type", "").replace("-", "_")
    theme = demande.get("theme", "")
    registre = demande.get("registre", "")
    filtres = {
        "niveau": a.niveau_valide(demande.get("niveau")),
        "type": type_piege if type_piege in v.TypePiege.values else None,
        "theme": theme
        if theme and m.Theme.objects.filter(slug=theme).exists()
        else None,
        "registre": registre if registre in v.Registre.values else None,
    }
    filtres.update(imposes or {})
    return filtres


def filtrer(entrees, filtres):
    """Les entrées qui passent tous les filtres à la fois."""
    if filtres["niveau"]:
        entrees = entrees.filter(niveau=filtres["niveau"])
    if filtres["type"]:
        pieges = a.publics(m.Piege.objects.filter(type_piege=filtres["type"]))
        entrees = entrees.filter(pk__in=pieges.values("entree"))
    if filtres["theme"]:
        entrees = entrees.filter(themes__slug=filtres["theme"])
    if filtres["registre"]:
        entrees = entrees.filter(registre=filtres["registre"])
    return entrees


def page_de_liste(request, titre, imposes=None):
    langue = get_language()
    filtres = filtres_demandes(request, imposes)
    entrees = filtrer(entrees_publiques(), filtres)
    page = Paginator(entrees, settings.ENTREES_PAR_PAGE).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "lexique/liste.html",
        {
            "titre": titre,
            "filtres": filtres,
            "page": page,
            "resumes": resumes(page.object_list, mon_niveau(request)),
            "choix_niveaux": v.NIVEAUX,
            "choix_types": v.TypePiege.choices,
            "choix_themes": themes_publics(langue),
            "choix_registres": v.Registre.choices,
        },
    )


def liste(request):
    return page_de_liste(request, _("Toutes les expressions"))


def par_niveau(request, niveau):
    code = a.niveau_valide(niveau)
    if code is None or niveau != code.lower():
        raise Http404
    return page_de_liste(
        request, _("Niveau %(niveau)s") % {"niveau": code}, {"niveau": code}
    )


def par_type(request, type_piege):
    code = type_piege.replace("-", "_")
    if code not in v.TypePiege.values or type_piege != slug_du_type(code):
        raise Http404
    return page_de_liste(request, v.TypePiege(code).label, {"type": code})


def par_theme(request, slug):
    theme = get_object_or_404(
        m.Theme.objects.prefetch_related("traductions"), slug=slug
    )
    nom, _langue = a.nom_du_theme(theme, get_language())
    return page_de_liste(request, nom, {"theme": slug})


# --- Fiche --------------------------------------------------------------------


def traduction_dans(traductions, langue):
    """La traduction de ``traductions`` (déjà filtrées) dans ``langue``, ou None."""
    if langue == "fr":
        return None
    return next((t for t in traductions if t.langue == langue), None)


def contenu_de_la_fiche(request, slug):
    """Ce que montrent la fiche et sa page à intégrer : le contenu relu, au niveau du lecteur.

    Un visiteur reçoit une 404 pour une entrée pas encore relue ; un relecteur
    connecté la voit, en aperçu.
    """
    apercu = a.voit_les_brouillons(request)
    entree = get_object_or_404(
        m.Entree.objects.select_related("ajoute_par__contributeur"), slug=slug
    )
    if not apercu and not a.est_public(entree):
        raise Http404
    langue = get_language()
    niveau_demande = mon_niveau(request)
    niveau = niveau_demande or entree.niveau
    versions = entree.sens()
    niveau_du_sens, sens = a.version_au_niveau(versions, niveau)

    pieges = []
    for piege in a.visibles(entree.pieges.prefetch_related("traductions"), apercu):
        niveau_explication, explication = a.version_au_niveau(
            piege.explications(), niveau
        )
        pieges.append(
            {
                "piege": piege,
                "niveau": niveau_explication,
                "explication": explication,
                "public": a.est_public(piege),
                "traduction": traduction_dans(
                    a.visibles(piege.traductions.all(), apercu), langue
                ),
            }
        )

    exemples = []
    rattachements = entree.liens_exemples.select_related("exemple").filter(
        exemple__in=a.visibles(m.Exemple.objects.all(), apercu)
    )
    for rattachement in rattachements:
        exemple = rattachement.exemple
        avant, mots, apres = a.decouper_surlignage(
            exemple.phrase, rattachement.surlignage
        )
        exemples.append(
            {
                "exemple": exemple,
                "avant": avant,
                "mots": mots,
                "apres": apres,
                "public": a.est_public(exemple),
                "traduction": traduction_dans(
                    a.visibles(exemple.traductions.all(), apercu), langue
                ),
            }
        )

    liens = []
    sortants = entree.liens_sortants.select_related("cible").filter(
        cible__in=a.visibles(m.Entree.objects.all(), apercu)
    )
    for type_lien, libelle in v.TypeLien.choices:
        cibles = [lien.cible for lien in sortants if lien.type_lien == type_lien]
        if cibles:
            liens.append({"type": type_lien, "libelle": libelle, "cibles": cibles})

    return {
        "entree": entree,
        "apercu": apercu,
        "public": a.est_public(entree),
        "sens": sens,
        "niveau_du_sens": niveau_du_sens,
        "niveau_demande": niveau_demande,
        "autres_niveaux": [n for n in versions if n != niveau_du_sens],
        "traduction": traduction_dans(
            a.visibles(entree.traductions.all(), apercu), langue
        ),
        "themes": [
            {"theme": theme, "nom": nom, "langue_du_nom": langue_du_nom}
            for theme in entree.themes.prefetch_related("traductions")
            for nom, langue_du_nom in [a.nom_du_theme(theme, langue)]
        ],
        "pieges": pieges,
        "exemples": exemples,
        "liens": liens,
        "auteur": entree.ajoute_par.contributeur.nom_affiche,
        "regions": [v.Region(code).label for code in entree.regions],
    }


def attribut_html(texte):
    """Le texte prêt à aller entre les guillemets d'un attribut HTML."""
    return (
        texte.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def code_d_integration(request, entree, niveau):
    """Le code <iframe> qu'un enseignant copie dans sa page (affiché comme du texte).

    C'est une simple chaîne : le gabarit l'échappe encore pour l'afficher, et
    la vedette y est déjà échappée pour l'attribut ``title`` de la page d'arrivée.
    """
    adresse = reverse("lexique:integrer", args=[entree.slug])
    if niveau:
        adresse += "?" + urlencode({"mon_niveau": niveau})
    titre = f"{entree} — Mots en commun"
    return (
        f'<iframe src="{attribut_html(request.build_absolute_uri(adresse))}" '
        f'title="{attribut_html(titre)}" width="100%" height="500" loading="lazy"></iframe>'
    )


def description_de_la_fiche(entree, traduction):
    """Le sens à montrer aux moteurs et aux aperçus : la traduction relue, sinon le français.

    Au niveau de l'entrée, comme sur son adresse canonique (sans « mon_niveau »).
    """
    if traduction and traduction.sens:
        return traduction.sens
    return a.version_au_niveau(entree.sens(), entree.niveau)[1]


def fiche(request, slug):
    contenu = contenu_de_la_fiche(request, slug)
    entree = contenu["entree"]
    contenu["code_integration"] = code_d_integration(
        request, entree, contenu["niveau_demande"]
    )
    contenu.update(reperes.reperes_de_la_fiche(request, entree))
    contenu["description"] = description_de_la_fiche(entree, contenu["traduction"])
    image = apercus.adresse(entree)
    contenu["image_d_apercu"] = request.build_absolute_uri(image) if image else None
    return render(request, "lexique/fiche.html", contenu)


@xframe_options_exempt
def integrer(request, slug):
    """La fiche seule, sans navigation : la seule page que d'autres sites peuvent encadrer.

    ``xframe_options_exempt`` retire « X-Frame-Options », et la politique de
    sécurité du contenu laisse alors tout site afficher la page (motsencommun/entetes.py).
    """
    contenu = contenu_de_la_fiche(request, slug)
    contenu["integration"] = True
    return render(request, "lexique/integrer.html", contenu)


# --- Recherche ----------------------------------------------------------------


def recherche(request):
    requete = request.GET.get("q", "").strip()
    resultats = (
        r.chercher(
            requete,
            get_language(),
            entrees=entrees_publiques(),
            traductions=a.publics(m.EntreeTraduction.objects.all()),
        )
        if requete
        else []
    )
    page = Paginator(resultats, settings.ENTREES_PAR_PAGE).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "lexique/recherche.html",
        {
            "requete": requete,
            "page": page,
            "resumes": resumes(page.object_list, mon_niveau(request)),
        },
    )


# --- Téléchargement et à propos -----------------------------------------------


#: Ce que contient chaque fichier, sur la page de téléchargement.
DESCRIPTIONS_DES_FICHIERS = {
    exportation.FICHIER_JSON: gettext_lazy(
        "Tout le contenu relu en un seul fichier : entrées, pièges, exemples, liens, "
        "traductions et crédits."
    ),
    "entrees.csv": gettext_lazy("Les entrées, une par ligne."),
    "pieges.csv": gettext_lazy("Les pièges, un par ligne."),
    "exemples.csv": gettext_lazy(
        "Les phrases d'exemple, une ligne par phrase et par entrée."
    ),
    "traductions.csv": gettext_lazy(
        "Les traductions relues, une ligne par texte traduit."
    ),
}


def adresse_de_telechargement(*parties):
    return settings.TELECHARGEMENTS_URL + "/".join(parties)


def telecharger(request):
    """Les fichiers du jour, le dictionnaire de données et les instantanés mensuels."""
    disponibles = dict(exportation.fichiers_disponibles())
    fichiers = [
        {
            "nom": nom,
            "adresse": adresse_de_telechargement(nom),
            "taille": disponibles[nom],
            "description": description,
        }
        for nom, description in DESCRIPTIONS_DES_FICHIERS.items()
        if nom in disponibles
    ]
    # Le dictionnaire dans la langue de la page, sinon en français.
    dictionnaire_ = next(
        (
            {"nom": nom, "adresse": adresse_de_telechargement(nom), "langue": langue}
            for langue, nom in (
                (get_language(), dictionnaire.nom_du_fichier(get_language())),
                (settings.LANGUAGE_CODE, dictionnaire.NOM_DU_FICHIER),
            )
            if nom in disponibles
        ),
        None,
    )
    instantanes = [
        {
            "mois": premier_du_mois,
            "fichiers": [
                {
                    "nom": nom,
                    "adresse": adresse_de_telechargement(
                        exportation.DOSSIER_INSTANTANES, mois, nom
                    ),
                }
                for nom in noms
            ],
        }
        for premier_du_mois, mois, noms in exportation.instantanes_disponibles()
    ]
    return render(
        request,
        "lexique/telecharger.html",
        {
            "fichiers": fichiers,
            "dictionnaire": dictionnaire_,
            "date_de_l_export": exportation.date_de_l_export(),
            "instantanes": instantanes,
        },
    )


def contributeurs_credites(langue):
    """Les noms de ceux qui ont ajouté ou approuvé du contenu public, triés selon la langue."""
    comptes = set()
    for modele in (
        m.Entree,
        m.Piege,
        m.Exemple,
        m.EntreeTraduction,
        m.PiegeTraduction,
        m.ExempleTraduction,
    ):
        comptes.update(
            a.publics(modele.objects.all()).values_list("ajoute_par", flat=True)
        )
    comptes.update(
        m.Relecture.objects.filter(decision=v.Decision.APPROUVE).values_list(
            "relecteur", flat=True
        )
    )
    noms = m.Contributeur.objects.filter(utilisateur__in=comptes).values_list(
        "nom_affiche", flat=True
    )
    return r.trier(noms, langue)


def a_propos(request):
    return render(
        request,
        "lexique/a_propos.html",
        {"contributeurs": contributeurs_credites(get_language())},
    )


# --- Pour les robots ------------------------------------------------------------


def robots_txt(request):
    """Les moteurs de recherche sont bienvenus ; les robots d'entraînement d'IA, envoyés aux téléchargements."""
    with translation.override(settings.LANGUAGE_CODE):
        adresse_telecharger = request.build_absolute_uri(reverse("lexique:telecharger"))
    return render(
        request,
        "lexique/robots.txt",
        {
            "robots_ia": settings.ROBOTS_D_ENTRAINEMENT_IA,
            "adresse_telecharger": adresse_telecharger,
            "adresse_plan": request.build_absolute_uri(reverse("plan_du_site")),
        },
        content_type="text/plain; charset=utf-8",
    )


def plan_du_site(request):
    """sitemap.xml : les adresses canoniques des pages publiques, entrées relues seulement."""
    return render(
        request,
        "lexique/sitemap.xml",
        {"adresses": reperes.adresses_du_plan(request)},
        content_type="application/xml; charset=utf-8",
    )

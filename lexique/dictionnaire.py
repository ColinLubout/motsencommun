"""Le dictionnaire de données : chaque champ et chaque code des fichiers à télécharger.

Il est écrit en français et se traduit comme le reste de l'interface (fichiers
.po) : « exporter » en écrit une version par langue du site,
``dictionnaire-de-donnees.md`` en français, ``dictionnaire-de-donnees.en.md``
en anglais, et ainsi de suite.
"""

from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from lexique import vocabulaire as v

NOM_DU_FICHIER = "dictionnaire-de-donnees.md"


def nom_du_fichier(langue):
    if langue == settings.LANGUAGE_CODE:
        return NOM_DU_FICHIER
    return NOM_DU_FICHIER.replace(".md", f".{langue}.md")


def fichiers_par_langue():
    """[(langue, nom du fichier)] : une version par langue du site, le français d'abord."""
    return [(code, nom_du_fichier(code)) for code, _nom in settings.LANGUAGES]


def noms_des_fichiers():
    return [nom for _langue, nom in fichiers_par_langue()]


# --- Les champs ---------------------------------------------------------------

COMMUNS = [
    (
        "statut",
        gettext_lazy(
            "Où en est la relecture (vocabulaire statut) : relu ou valide, ou retire "
            "pour ce qui a été retiré après sa publication. Un contenu retiré garde "
            "ici sa dernière version publiée."
        ),
    ),
    ("ajoute_par", gettext_lazy("Le nom affiché de la personne qui l'a ajouté.")),
    ("relecteurs", gettext_lazy("Les noms affichés des personnes qui l'ont approuvé.")),
    (
        "cree_le, modifie_le",
        gettext_lazy(
            "Date et heure de sa création et de sa dernière modification, en temps "
            "universel (ISO 8601)."
        ),
    ),
]

EN_TETE = [
    ("titre", gettext_lazy("Le nom du projet.")),
    (
        "exporte_le",
        gettext_lazy("Quand le fichier a été écrit, en temps universel (ISO 8601)."),
    ),
    (
        "licence",
        gettext_lazy(
            "La licence des données (nom, adresse) et le crédit à donner pour les "
            "réutiliser."
        ),
    ),
    ("dictionnaire_de_donnees", gettext_lazy("Le nom de ce document.")),
    (
        "contributeurs",
        gettext_lazy(
            "Les noms affichés de toutes les personnes qui ont ajouté ou approuvé "
            "quelque chose dans le fichier."
        ),
    ),
    (
        "themes",
        gettext_lazy(
            "Les thèmes des entrées : slug, nom en français, et traductions du nom "
            "par code de langue."
        ),
    ),
    ("entrees", gettext_lazy("Les entrées, décrites ci-dessous.")),
]

ENTREES = [
    (
        "slug",
        gettext_lazy(
            "L'identifiant permanent de l'entrée, en ASCII, tiré de la vedette. Il ne "
            "change jamais, même si la vedette est corrigée : c'est aussi l'adresse "
            "de sa fiche, `/fr/expressions/<slug>/`."
        ),
    ),
    (
        "vedette",
        gettext_lazy(
            "Le mot ou l'expression, dans sa forme de citation : « poser un lapin à qqn »."
        ),
    ),
    (
        "precision",
        gettext_lazy(
            "Ce qui distingue deux entrées de même vedette, comme « avant le nom ». "
            "Le plus souvent vide."
        ),
    ),
    (
        "type_entree",
        gettext_lazy("Mot, expression ou construction (vocabulaire type_entree)."),
    ),
    ("nature", gettext_lazy("La nature grammaticale (vocabulaire nature).")),
    (
        "genre",
        gettext_lazy(
            "Le genre d'un nom (vocabulaire genre) ; vide pour les autres entrées."
        ),
    ),
    ("api", gettext_lazy("La prononciation, en alphabet phonétique international.")),
    (
        "sens_a1 … sens_c2",
        gettext_lazy(
            "Le sens, expliqué en français à chaque niveau du CECRL, en une à trois "
            "phrases. Tous les niveaux ne sont pas écrits : celui de l'entrée l'est "
            "d'abord."
        ),
    ),
    (
        "sens_litteral",
        gettext_lazy(
            "Ce que disent les mots pris un à un, pour une expression imagée."
        ),
    ),
    ("niveau", gettext_lazy("Le niveau du CECRL de l'entrée (vocabulaire niveau).")),
    ("registre", gettext_lazy("Le registre de langue (vocabulaire registre).")),
    ("frequence", gettext_lazy("La fréquence d'emploi (vocabulaire frequence).")),
    (
        "regions",
        gettext_lazy(
            "Les régions où l'entrée s'emploie (vocabulaire region). Une liste vide "
            "veut dire : partout."
        ),
    ),
    (
        "themes",
        gettext_lazy(
            "Les slugs des thèmes de l'entrée. Leurs noms sont dans la liste themes "
            "du JSON, et leurs traductions aussi dans traductions.csv."
        ),
    ),
    (
        "formes",
        gettext_lazy(
            "D'autres façons d'écrire l'entrée, que la recherche trouve : "
            "« j'en ai marre », « t'en as marre »…"
        ),
    ),
    (
        "liens",
        gettext_lazy(
            "JSON seulement. Les entrées liées : type_lien (vocabulaire type_lien) et "
            "cible, le slug de l'autre entrée."
        ),
    ),
    (
        "voir_aussi, contraire, a_ne_pas_confondre, variante",
        gettext_lazy(
            "CSV seulement. Les mêmes liens, une colonne par type : les slugs des "
            "entrées liées."
        ),
    ),
    (
        "pieges",
        gettext_lazy("JSON seulement. Les pièges de l'entrée, décrits plus bas."),
    ),
    (
        "exemples",
        gettext_lazy("JSON seulement. Ses phrases d'exemple, décrites plus bas."),
    ),
    (
        "traductions",
        gettext_lazy("JSON seulement. Ses traductions relues, décrites plus bas."),
    ),
]

PIEGES = [
    ("id", gettext_lazy("L'identifiant numérique du piège. Il ne change pas.")),
    ("entree", gettext_lazy("CSV seulement. Le slug de l'entrée du piège.")),
    ("type_piege", gettext_lazy("Le genre de piège (vocabulaire type_piege).")),
    (
        "concerne",
        gettext_lazy(
            "Ce que le piège gêne : comprendre, s'exprimer, ou les deux (vocabulaire "
            "concerne)."
        ),
    ),
    ("gravite", gettext_lazy("À quel point l'erreur gêne (vocabulaire gravite).")),
    (
        "langue_apprenant",
        gettext_lazy(
            "Le code de la langue de l'apprenant quand le piège en dépend (en pour un "
            "faux ami des anglophones) ; vide quand il vaut pour tous."
        ),
    ),
    (
        "declencheur",
        gettext_lazy(
            "Le mot de la langue de l'apprenant qui tend le piège : « actually »."
        ),
    ),
    (
        "explication_a1 … explication_c2",
        gettext_lazy(
            "Pourquoi l'entrée trompe, expliqué en français à chaque niveau du CECRL."
        ),
    ),
    (
        "incorrect, correct",
        gettext_lazy(
            "Une paire minimale : ce qu'il ne faut pas dire, et ce qu'il faut dire."
        ),
    ),
    (
        "traductions",
        gettext_lazy("JSON seulement. Les traductions relues de l'explication."),
    ),
]

EXEMPLES = [
    (
        "id",
        gettext_lazy(
            "L'identifiant numérique de la phrase. Une phrase qui illustre plusieurs "
            "entrées garde le même id partout."
        ),
    ),
    (
        "entree",
        gettext_lazy(
            "CSV seulement. Le slug de l'entrée illustrée : une phrase qui illustre "
            "deux entrées occupe deux lignes."
        ),
    ),
    ("phrase", gettext_lazy("La phrase, en français.")),
    (
        "surlignage",
        gettext_lazy(
            "Les mots exacts de la phrase qui montrent l'entrée ; le site les surligne."
        ),
    ),
    ("ordre", gettext_lazy("La place de la phrase parmi les exemples de l'entrée.")),
    ("niveau", gettext_lazy("Le niveau du CECRL de la phrase entière.")),
    (
        "traductions",
        gettext_lazy("JSON seulement. Les traductions relues de la phrase."),
    ),
]

TRADUCTIONS_JSON = [
    (
        "sens, sens_litteral",
        gettext_lazy(
            "Pour une entrée : le sens dans cette langue (une seule version, pas une "
            "par niveau), et la lecture mot à mot."
        ),
    ),
    ("explication", gettext_lazy("Pour un piège : l'explication dans cette langue.")),
    ("traduction", gettext_lazy("Pour un exemple : la phrase dans cette langue.")),
]

TRADUCTIONS_CSV = [
    ("objet", gettext_lazy("Ce qui est traduit : entree, piege, exemple ou theme.")),
    (
        "cle",
        gettext_lazy(
            "Le slug de l'entrée ou du thème, ou l'id du piège ou de l'exemple."
        ),
    ),
    ("langue", gettext_lazy("Le code ISO 639-1 de la langue de la traduction.")),
    (
        "champ",
        gettext_lazy(
            "Le champ traduit : sens, sens_litteral, explication, traduction ou nom."
        ),
    ),
    ("texte", gettext_lazy("Le texte traduit.")),
    (
        "statut, ajoute_par, relecteurs, cree_le, modifie_le",
        gettext_lazy(
            "Comme pour le reste du contenu. Vides pour les noms des thèmes, que le "
            "propriétaire du site gère sans relecture."
        ),
    ),
]

#: Chaque vocabulaire, sous le nom qu'il porte dans les descriptions.
VOCABULAIRES = [
    ("niveau", v.Niveau),
    ("type_entree", v.TypeEntree),
    ("nature", v.Nature),
    ("genre", v.Genre),
    ("registre", v.Registre),
    ("frequence", v.Frequence),
    ("region", v.Region),
    ("type_piege", v.TypePiege),
    ("concerne", v.Concerne),
    ("gravite", v.Gravite),
    ("type_lien", v.TypeLien),
    ("statut", v.Statut),
]


# --- Le document --------------------------------------------------------------


def cellule(texte):
    """Un texte dans une case de tableau Markdown : « | » ne coupe pas la case."""
    return str(texte).replace("|", "\\|")


def tableau(entetes, lignes):
    resultat = [
        "| " + " | ".join(entetes) + " |",
        "| " + " | ".join("---" for _e in entetes) + " |",
    ]
    resultat += [
        "| " + " | ".join(cellule(c) for c in ligne) + " |" for ligne in lignes
    ]
    return "\n".join(resultat)


def champs(lignes):
    return tableau(
        [_("Champ"), _("Description")],
        [(f"`{nom}`", description) for nom, description in lignes],
    )


def rediger(langue):
    """Le dictionnaire de données en Markdown, dans ``langue``."""
    with translation.override(langue):
        parties = [
            "# " + _("Dictionnaire de données de Mots en commun"),
            _(
                "Ce document décrit les fichiers à télécharger de Mots en commun, "
                "champ par champ et code par code. Les données sont sous licence "
                "CC BY 4.0 : pour les réutiliser, créditez-les « Contributeurs de "
                "Mots en commun »."
            ),
            "## " + _("Les fichiers"),
            tableau(
                [_("Fichier"), _("Contenu")],
                [
                    (
                        "`mots-en-commun.json`",
                        _(
                            "Toutes les entrées, avec leurs pièges, exemples, liens et "
                            "traductions, et en tête la date, la licence et les crédits."
                        ),
                    ),
                    ("`entrees.csv`", _("Les entrées, une par ligne.")),
                    ("`pieges.csv`", _("Les pièges, un par ligne.")),
                    (
                        "`exemples.csv`",
                        _("Les phrases d'exemple, une ligne par phrase et par entrée."),
                    ),
                    (
                        "`traductions.csv`",
                        _("Les traductions relues, une ligne par texte traduit."),
                    ),
                    (f"`{NOM_DU_FICHIER}`", _("Ce document.")),
                ],
            ),
            "## " + _("Règles communes"),
            "\n".join(
                f"- {regle}"
                for regle in (
                    _(
                        "Seul le contenu relu est publié : statut relu ou valide, plus "
                        "retire pour ce qui a été retiré après sa publication. Les "
                        "brouillons, ce qui attend sa relecture et ce qui a été refusé "
                        "restent sur le serveur."
                    ),
                    _(
                        "Les noms des champs sont ceux de la base de données, en "
                        "français sans accents. Les codes (niveau, registre…) ne "
                        "changent jamais ; leurs libellés sont dans les vocabulaires, "
                        "plus bas."
                    ),
                    _(
                        "Tout est en UTF-8. Les CSV commencent par une marque d'ordre "
                        "des octets (BOM), pour que les tableurs affichent bien le "
                        "cyrillique et le polonais. Leurs colonnes sont séparées par "
                        "des virgules ; une liste tient dans une seule case, ses "
                        "éléments séparés par une barre verticale entourée d'espaces."
                    ),
                    _(
                        "Un champ vide vaut null dans le JSON, et une case vide dans "
                        "les CSV."
                    ),
                    _(
                        "Les dates sont en temps universel, au format ISO 8601 : "
                        "2026-11-23T03:30:00Z."
                    ),
                    _(
                        "Les fichiers sont refaits chaque nuit. Le premier de chaque "
                        "mois, une copie datée est gardée pour toujours, dans "
                        "instantanes/AAAA-MM/ : citez-la pour renvoyer à une version "
                        "précise."
                    ),
                    _(
                        "Seuls les noms affichés des contributeurs sont publiés : ni "
                        "adresse e-mail, ni compte, ni historique des modifications."
                    ),
                )
            ),
            "## " + _("En-tête du JSON"),
            champs(EN_TETE),
            "## " + _("Entrées"),
            _(
                "Dans le JSON, chaque élément de « entrees » ; dans entrees.csv, "
                "chaque ligne."
            ),
            champs([*ENTREES, *COMMUNS]),
            "## " + _("Pièges"),
            _("Dans le JSON, dans « pieges » de chaque entrée ; dans pieges.csv."),
            champs([*PIEGES, *COMMUNS]),
            "## " + _("Exemples"),
            _("Dans le JSON, dans « exemples » de chaque entrée ; dans exemples.csv."),
            champs([*EXEMPLES, *COMMUNS]),
            "## " + _("Traductions"),
            _(
                "Dans le JSON, « traductions » est un objet dont les clés sont des "
                "codes de langue ISO 639-1 (en, pl, uk…). Chaque traduction a ces "
                "champs :"
            ),
            champs([*TRADUCTIONS_JSON, *COMMUNS]),
            _("Dans traductions.csv, une ligne par texte traduit :"),
            champs(TRADUCTIONS_CSV),
            "## " + _("Vocabulaires"),
            _(
                "Chaque code, avec son libellé. Les langues (langue, "
                "langue_apprenant) sont des codes ISO 639-1 à deux lettres : fr, "
                "en, pl, uk…"
            ),
        ]
        for nom, choix in VOCABULAIRES:
            parties.append(f"### {nom}")
            parties.append(
                tableau(
                    [_("Code"), _("Libellé")],
                    [(f"`{code}`", libelle) for code, libelle in choix.choices],
                )
            )
        return "\n\n".join(str(partie) for partie in parties) + "\n"

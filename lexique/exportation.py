"""Les fichiers à télécharger : le contenu relu, en JSON et en CSV, avec ses crédits.

Règles du PRD (« Downloads and licence ») :

- seul le contenu relu ou validé est exporté, plus ce qui a été retiré après sa
  publication (marqué « retire », pour qu'un slug ne disparaisse jamais) ; les
  brouillons, ce qui est en relecture et ce qui est refusé restent sur le serveur ;
- un contenu retiré apparaît dans sa dernière version publiée, tirée de
  l'historique : un texte qui n'a jamais été relu ne sort jamais ;
- chaque enregistrement porte son statut, et les noms affichés de qui l'a
  ajouté (``ajoute_par``) et approuvé (``relecteurs``) ; ni adresse e-mail, ni
  nom de compte, ni historique ;
- les noms des champs sont ceux du modèle, en français.

Les fichiers sont écrits d'un coup (fichier provisoire puis renommage) : Caddy,
qui les sert, ne donne jamais un fichier à moitié écrit.
"""

import csv
import datetime
import io
import json
import os
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from lexique import dictionnaire
from lexique import models as m
from lexique import recherche as r
from lexique import vocabulaire as v

FICHIER_JSON = "mots-en-commun.json"
FICHIERS_CSV = ["entrees.csv", "pieges.csv", "exemples.csv", "traductions.csv"]
DOSSIER_INSTANTANES = "instantanes"
#: Une liste dans une case de CSV : ses éléments séparés par « | ».
SEPARATEUR = " | "
LICENCE = {
    "nom": "CC BY 4.0",
    "adresse": "https://creativecommons.org/licenses/by/4.0/",
    "credit": "Contributeurs de Mots en commun",
}

#: Ce qui peut sortir : le contenu public, et ce qui a été retiré après sa publication.
STATUTS_EXPORTES = [*v.STATUTS_PUBLICS, v.Statut.RETIRE]

NIVEAUX = [niveau.lower() for niveau in v.NIVEAUX]
CHAMPS_ENTREE = [
    "slug",
    "vedette",
    "precision",
    "type_entree",
    "nature",
    "genre",
    "api",
    *(f"sens_{niveau}" for niveau in NIVEAUX),
    "sens_litteral",
    "niveau",
    "registre",
    "frequence",
    "regions",
    "themes",
    "formes",
]
CHAMPS_PIEGE = [
    "id",
    "type_piege",
    "concerne",
    "gravite",
    "langue_apprenant",
    "declencheur",
    *(f"explication_{niveau}" for niveau in NIVEAUX),
    "incorrect",
    "correct",
]
CHAMPS_EXEMPLE = ["id", "phrase", "surlignage", "ordre", "niveau"]
CHAMPS_COMMUNS = ["statut", "ajoute_par", "relecteurs", "cree_le", "modifie_le"]
#: Les champs de chaque table de traductions.
CHAMPS_TRADUITS = {
    "entree": ["sens", "sens_litteral"],
    "piege": ["explication"],
    "exemple": ["traduction"],
}

COLONNES = {
    "entrees.csv": [
        *CHAMPS_ENTREE,
        *v.TypeLien.values,
        *CHAMPS_COMMUNS,
    ],
    "pieges.csv": ["id", "entree", *CHAMPS_PIEGE[1:], *CHAMPS_COMMUNS],
    "exemples.csv": ["id", "entree", *CHAMPS_EXEMPLE[1:], *CHAMPS_COMMUNS],
    "traductions.csv": ["objet", "cle", "langue", "champ", "texte", *CHAMPS_COMMUNS],
}

INSTANTANE = re.compile(r"\d{4}-\d{2}")


# --- Ce qui sort --------------------------------------------------------------


def version_publiee(contenu):
    """La version à exporter, ou None si le contenu ne sort pas.

    Relu ou validé : le contenu tel quel. Retiré : sa dernière version publiée,
    tirée de l'historique, avec le statut « retire » ; s'il n'a jamais été
    publié, il ne sort pas. Tout autre statut : None.
    """
    if contenu.statut in v.STATUTS_PUBLICS:
        return contenu
    if contenu.statut != v.Statut.RETIRE:
        return None
    publiee = (
        contenu.history.filter(statut__in=v.STATUTS_PUBLICS)
        .order_by("-history_date", "-history_id")
        .first()
    )
    if publiee is None:
        return None
    version = publiee.instance
    version.statut = contenu.statut
    return version


def date_iso(moment):
    return moment.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def ou_null(valeur):
    """Un texte vide devient null : « pas renseigné », pas « texte vide »."""
    if isinstance(valeur, str) and not valeur.strip():
        return None
    return valeur


class Exportation:
    """Rassemble le contenu à publier, avec les noms à créditer."""

    def __init__(self):
        self.noms = dict(
            m.Contributeur.objects.values_list("utilisateur_id", "nom_affiche")
        )
        self.approbations = {}
        for type_contenu, id_contenu, relecteur in m.Relecture.objects.filter(
            decision=v.Decision.APPROUVE
        ).values_list("type_contenu_id", "id_contenu", "relecteur_id"):
            self.approbations.setdefault((type_contenu, id_contenu), set()).add(
                relecteur
            )
        self.credites = set()

    # Crédits et champs communs

    def communs(self, contenu, version):
        type_contenu = ContentType.objects.get_for_model(type(contenu)).pk
        auteur = self.noms.get(version.ajoute_par_id)
        relecteurs = r.trier(
            {
                self.noms[compte]
                for compte in self.approbations.get((type_contenu, contenu.pk), ())
                if compte in self.noms
            },
            "fr",
        )
        self.credites.update(filter(None, [auteur, *relecteurs]))
        return {
            "statut": contenu.statut,
            "ajoute_par": auteur,
            "relecteurs": relecteurs,
            "cree_le": date_iso(contenu.cree_le),
            "modifie_le": date_iso(contenu.modifie_le),
        }

    def traductions(self, traductions, champs):
        """{langue: {champs traduits…, statut, crédits}}, traductions exportées seulement."""
        resultat = {}
        for traduction in sorted(traductions, key=lambda t: t.langue):
            version = version_publiee(traduction)
            if version is not None:
                resultat[traduction.langue] = {
                    **{champ: ou_null(getattr(version, champ)) for champ in champs},
                    **self.communs(traduction, version),
                }
        return resultat

    # Les enregistrements

    def piege(self, piege):
        version = version_publiee(piege)
        if version is None:
            return None
        return {
            **{champ: ou_null(getattr(version, champ)) for champ in CHAMPS_PIEGE},
            **self.communs(piege, version),
            "traductions": self.traductions(
                piege.traductions.all(), CHAMPS_TRADUITS["piege"]
            ),
        }

    def exemple(self, lien):
        exemple = lien.exemple
        version = version_publiee(exemple)
        if version is None:
            return None
        return {
            "id": exemple.pk,
            "phrase": version.phrase,
            "surlignage": lien.surlignage,
            "ordre": lien.ordre,
            "niveau": version.niveau,
            **self.communs(exemple, version),
            "traductions": self.traductions(
                exemple.traductions.all(), CHAMPS_TRADUITS["exemple"]
            ),
        }

    def entree(self, entree, version, slugs_exportes):
        valeurs = {}
        for champ in CHAMPS_ENTREE:
            if champ == "themes":
                valeurs[champ] = sorted(theme.slug for theme in entree.themes.all())
            else:
                valeurs[champ] = ou_null(getattr(version, champ))
        liens = sorted(
            (
                {"type_lien": lien.type_lien, "cible": slugs_exportes[lien.cible_id]}
                for lien in entree.liens_sortants.all()
                if lien.cible_id in slugs_exportes
            ),
            key=lambda lien: (
                v.TypeLien.values.index(lien["type_lien"]),
                lien["cible"],
            ),
        )
        return {
            **valeurs,
            **self.communs(entree, version),
            "pieges": list(filter(None, map(self.piege, entree.pieges.all()))),
            "exemples": list(
                filter(None, map(self.exemple, entree.liens_exemples.all()))
            ),
            "liens": liens,
            "traductions": self.traductions(
                entree.traductions.all(), CHAMPS_TRADUITS["entree"]
            ),
        }

    def donnees(self, exporte_le=None):
        """Tout ce que contient mots-en-commun.json."""
        entrees = m.Entree.objects.filter(statut__in=STATUTS_EXPORTES).prefetch_related(
            "themes",
            "traductions",
            "liens_sortants",
            "pieges__traductions",
            "liens_exemples__exemple__traductions",
        )
        versions = [
            (entree, version)
            for entree in entrees
            if (version := version_publiee(entree)) is not None
        ]
        slugs_exportes = {entree.pk: entree.slug for entree, _version in versions}
        exportees = [
            self.entree(entree, version, slugs_exportes) for entree, version in versions
        ]
        themes = (
            m.Theme.objects.filter(entrees__in=list(slugs_exportes))
            .distinct()
            .prefetch_related("traductions")
            .order_by("slug")
        )
        return {
            "titre": "Mots en commun",
            "exporte_le": date_iso(exporte_le or timezone.now()),
            "licence": LICENCE,
            "dictionnaire_de_donnees": dictionnaire.NOM_DU_FICHIER,
            "contributeurs": r.trier(self.credites, "fr"),
            "themes": [
                {
                    "slug": theme.slug,
                    "nom": theme.nom,
                    "traductions": {
                        t.langue: t.nom
                        for t in sorted(theme.traductions.all(), key=lambda t: t.langue)
                    },
                }
                for theme in themes
            ],
            "entrees": exportees,
        }


# --- Les fichiers -------------------------------------------------------------


def cellule(valeur):
    """Une valeur du JSON dans une case de CSV : null vide, liste jointe par « | »."""
    if valeur is None:
        return ""
    if isinstance(valeur, list):
        return SEPARATEUR.join(str(element) for element in valeur)
    return str(valeur)


def lignes(donnees):
    """Les lignes de chaque CSV, tirées du même contenu que le JSON."""
    tables = {nom: [] for nom in FICHIERS_CSV}
    vues = set()

    def traduction(objet, cle, traductions):
        for langue, valeurs in traductions.items():
            for champ in CHAMPS_TRADUITS[objet]:
                if (
                    valeurs[champ] is not None
                    and (objet, cle, langue, champ) not in vues
                ):
                    vues.add((objet, cle, langue, champ))
                    tables["traductions.csv"].append(
                        {
                            "objet": objet,
                            "cle": cle,
                            "langue": langue,
                            "champ": champ,
                            "texte": valeurs[champ],
                            **{c: valeurs[c] for c in CHAMPS_COMMUNS},
                        }
                    )

    for entree in donnees["entrees"]:
        liens = {
            type_lien: [
                lien["cible"]
                for lien in entree["liens"]
                if lien["type_lien"] == type_lien
            ]
            for type_lien in v.TypeLien.values
        }
        tables["entrees.csv"].append({**entree, **liens})
        traduction("entree", entree["slug"], entree["traductions"])
        for piege in entree["pieges"]:
            tables["pieges.csv"].append({**piege, "entree": entree["slug"]})
            traduction("piege", piege["id"], piege["traductions"])
        for exemple in entree["exemples"]:
            tables["exemples.csv"].append({**exemple, "entree": entree["slug"]})
            traduction("exemple", exemple["id"], exemple["traductions"])
    for theme in donnees["themes"]:
        for langue, nom in theme["traductions"].items():
            tables["traductions.csv"].append(
                {
                    "objet": "theme",
                    "cle": theme["slug"],
                    "langue": langue,
                    "champ": "nom",
                    "texte": nom,
                }
            )
    return tables


def en_csv(nom, lignes_de_la_table):
    """Le CSV en octets : UTF-8 avec BOM, pour que les tableurs lisent bien toutes les écritures."""
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, lineterminator="\r\n")
    ecrivain.writerow(COLONNES[nom])
    for ligne in lignes_de_la_table:
        ecrivain.writerow([cellule(ligne.get(colonne)) for colonne in COLONNES[nom]])
    return tampon.getvalue().encode("utf-8-sig")


def ecrire(chemin, octets):
    """Écrit le fichier d'un coup : personne ne télécharge un fichier à moitié écrit."""
    provisoire = chemin.with_name(f".{chemin.name}.provisoire")
    provisoire.write_bytes(octets)
    os.replace(provisoire, chemin)


def dossier_des_telechargements():
    return Path(settings.DOSSIER_TELECHARGEMENTS)


def fichiers_courants():
    """Les noms des fichiers qu'« exporter » écrit, dans l'ordre de la page de téléchargement."""
    return [FICHIER_JSON, *FICHIERS_CSV, *dictionnaire.noms_des_fichiers()]


def exporter(exporte_le=None):
    """Écrit tous les fichiers à télécharger. Renvoie le nombre d'entrées exportées."""
    dossier = dossier_des_telechargements()
    dossier.mkdir(parents=True, exist_ok=True)
    donnees = Exportation().donnees(exporte_le)
    ecrire(
        dossier / FICHIER_JSON,
        (json.dumps(donnees, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    for nom, contenu in lignes(donnees).items():
        ecrire(dossier / nom, en_csv(nom, contenu))
    for langue, nom in dictionnaire.fichiers_par_langue():
        ecrire(dossier / nom, dictionnaire.rediger(langue).encode("utf-8"))
    return len(donnees["entrees"])


# --- Instantanés mensuels -----------------------------------------------------


def nom_date(nom, mois):
    """« mots-en-commun.json » → « mots-en-commun-2026-12.json »."""
    radical, _point, extension = nom.partition(".")
    return f"{radical}-{mois}.{extension}"


def enregistrer_instantane(mois):
    """Copie les fichiers du jour dans instantanes/AAAA-MM/, s'il n'y en a pas déjà.

    Un instantané est gardé pour toujours, tel quel : on ne le remplace jamais.
    Renvoie True s'il vient d'être créé.
    """
    dossier = dossier_des_telechargements()
    cible = dossier / DOSSIER_INSTANTANES / mois
    if cible.exists():
        return False
    provisoire = cible.with_name(f".{mois}.provisoire")
    shutil.rmtree(provisoire, ignore_errors=True)
    provisoire.mkdir(parents=True)
    for nom in fichiers_courants():
        shutil.copy2(dossier / nom, provisoire / nom_date(nom, mois))
    os.replace(provisoire, cible)
    return True


# --- Ce que montre la page de téléchargement ----------------------------------


def fichiers_disponibles():
    """Les fichiers du jour qui existent : [(nom, taille en octets)]."""
    dossier = dossier_des_telechargements()
    return [
        (nom, (dossier / nom).stat().st_size)
        for nom in fichiers_courants()
        if (dossier / nom).is_file()
    ]


def date_de_l_export():
    """Quand les fichiers du jour ont été écrits, ou None."""
    chemin = dossier_des_telechargements() / FICHIER_JSON
    if not chemin.is_file():
        return None
    return datetime.datetime.fromtimestamp(chemin.stat().st_mtime, tz=datetime.UTC)


def instantanes_disponibles():
    """Les instantanés mensuels, du plus récent au plus ancien : [(1er du mois, "AAAA-MM", [noms])]."""
    dossier = dossier_des_telechargements() / DOSSIER_INSTANTANES
    if not dossier.is_dir():
        return []
    resultat = []
    for mois in sorted(
        (
            d.name
            for d in dossier.iterdir()
            if d.is_dir() and INSTANTANE.fullmatch(d.name)
        ),
        reverse=True,
    ):
        noms = [nom_date(nom, mois) for nom in fichiers_courants()]
        presents = [nom for nom in noms if (dossier / mois / nom).is_file()]
        annee, numero = map(int, mois.split("-"))
        resultat.append((datetime.date(annee, numero, 1), mois, presents))
    return resultat

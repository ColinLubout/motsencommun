"""Import des données initiales : l'archive ``donnees/import/donnees-initiales.zip``.

Ces données ont été rédigées par une IA et ne servent qu'aux essais. Tout ce que
l'import crée reste en brouillon, porte la marque ``genere_par_ia`` et est
attribué au compte système ``import-initial``. Le site en ligne est déployé à
partir d'une base vide, sans cet import.

Les correspondances suivent la table de la section « Seed data » du PRD. Le
texte anglais va dans les traductions (``langue = en``) ; les explications en
français restent vides.

Relancer l'import ne crée jamais de doublon. Une entrée dont le slug existe déjà
est laissée telle quelle, avec ses pièges et ses traductions ; un exemple déjà
importé (même phrase) n'est pas recréé. Rien n'est rattaché à une entrée ou à un
exemple créés à la main. Une entrée de départ supprimée puis réimportée retrouve
ses pièges, ses liens et ses exemples.
"""

import collections
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import yaml
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from lexique import models as m

NOM_DU_COMPTE = "import-initial"
LANGUE_DES_DONNEES = "en"

# --- Correspondances (table du PRD) -------------------------------------------

TYPES_ENTREE = {
    "word": "mot",
    "expression": "expression",
    "construction": "construction",
}

NATURES = {
    "noun": "nom",
    "verb": "verbe",
    "adjective": "adjectif",
    "adverb": "adverbe",
    "preposition": "preposition",
    "conjunction": "conjonction",
    "pronoun": "pronom",
    "determiner": "determinant",
    "numeral": "numeral",
    "interjection": "interjection",
    "verb_phrase": "locution_verbale",
    "noun_phrase": "locution_nominale",
    "adjectival_phrase": "locution_adjectivale",
    "adverbial_phrase": "locution_adverbiale",
    "prepositional_phrase": "locution_prepositionnelle",
    "conjunctional_phrase": "locution_conjonctive",
    "sentence": "phrase",
}

GENRES = {
    "m": "masculin",
    "f": "feminin",
    "epicene": "epicene",
    "plural_only": "pluriel_seulement",
}

FREQUENCES = {
    "very_common": "tres_courante",
    "common": "courante",
    "uncommon": "peu_courante",
    "rare": "rare",
}

#: Thème de départ : (slug, nom en français).
THEMES = {
    "emotions": ("emotions", "Émotions"),
    "relationships": ("relations", "Relations"),
    "social": ("vie-sociale", "Vie sociale"),
    "conversation": ("conversation", "Conversation"),
    "communication": ("communication", "Communication"),
    "money": ("argent", "Argent"),
    "food": ("nourriture", "Nourriture"),
    "work": ("travail", "Travail"),
    "time": ("temps", "Temps et durée"),
    "weather": ("meteo", "Météo"),
    "health": ("sante", "Santé"),
    "home": ("maison", "Maison"),
    "family": ("famille", "Famille"),
    "travel": ("voyages", "Voyages"),
    "places": ("lieux", "Lieux"),
    "culture": ("culture", "Culture"),
    "numbers": ("nombres", "Nombres"),
}

TYPES_LIEN = {
    "contrast": "a_ne_pas_confondre",
    "see_also": "voir_aussi",
    "synonym": "voir_aussi",
    "antonym": "contraire",
    "variant": "variante",
}

TYPES_PIEGE = {
    "non_compositional": "sens_figure",
    "false_friend": "faux_ami",
    "partial_false_friend": "faux_ami_partiel",
    "connotation": "connotation",
    "calque": "calque",
    "argument_structure": "construction_inversee",
    "meaning_by_position": "sens_selon_position",
    "gender_meaning": "sens_selon_genre",
    "polarity": "polarite",
    "pronunciation": "prononciation",
    "mood_trigger": "mode_impose",
    "preposition": "preposition",
    "fixed_form": "forme_figee",
    "confusable": "confusion_possible",
    "irregular_form": "forme_irreguliere",
    "register": "registre",
    "regional": "regional",
    "pragmatic": "pragmatique",
}

GRAVITES = {"low": "faible", "medium": "moyenne", "high": "elevee"}

#: Les seuls pièges dont la langue de l'apprenant est renseignée (« l1 »).
PIEGES_SELON_LA_LANGUE = frozenset(
    {
        "faux_ami",
        "faux_ami_partiel",
        "calque",
        "connotation",
        "preposition",
        "construction_inversee",
    }
)

#: « sense_label » est en anglais ; « précision » s'affiche en français à côté de
#: la vedette. Les étiquettes déjà en français (« penser à »…) restent telles quelles.
PRECISIONS = {
    "before the noun": "avant le nom",
    "after the noun": "après le nom",
    "OK, deal": "d'accord",
    "dear": "affection",
    "expensive": "prix",
    "Québec, Belgium, Switzerland": "Québec, Belgique, Suisse",
    "France": "France",
    "miss a train or chance": "rater un train, une occasion",
    "nonsense": "bêtises",
    "more": "davantage",
    "no longer": "ne… plus",
    "carry out": "accomplir",
    "become aware": "se rendre compte",
}


class ErreurDImport(Exception):
    """Les données ne peuvent pas être importées ; le message dit où et pourquoi."""


@dataclass
class Bilan:
    """Ce que l'import a créé, et les entrées déjà présentes qu'il a laissées."""

    crees: collections.Counter = field(default_factory=collections.Counter)
    entrees_deja_presentes: list = field(default_factory=list)

    @property
    def rien_de_nouveau(self):
        return not any(self.crees.values())


# --- Lecture de l'archive -----------------------------------------------------


def lire_archive(chemin):
    """Les fiches d'entrées et les lots de phrases, lus dans le zip ou dans un dossier.

    Renvoie deux listes de couples (nom du fichier, contenu YAML lu) : les fiches
    (``data/items/*.yaml``) et les lots de phrases (``data/sentences/*.yaml``),
    chacune triée par nom de fichier.
    """
    chemin = Path(chemin)
    if chemin.is_dir():
        fichiers = {
            fichier.relative_to(chemin).as_posix(): fichier.read_bytes
            for fichier in chemin.rglob("*.yaml")
        }
        return _ranger(fichiers)
    if chemin.is_file() and zipfile.is_zipfile(chemin):
        with zipfile.ZipFile(chemin) as archive:
            fichiers = {
                nom: (lambda nom=nom: archive.read(nom))
                for nom in archive.namelist()
                if nom.endswith(".yaml")
            }
            return _ranger(fichiers)
    raise ErreurDImport(
        f"« {chemin} » n'est ni l'archive donnees-initiales.zip, ni le dossier qui en "
        "est extrait."
    )


def _ranger(fichiers):
    fiches, lots = [], []
    for nom in sorted(fichiers):
        dossier = PurePosixPath(nom).parts[-3:-1]
        if dossier == ("data", "items"):
            fiches.append((nom, _lire_yaml(nom, fichiers[nom]())))
        elif dossier == ("data", "sentences"):
            lots.append((nom, _lire_yaml(nom, fichiers[nom]())))
    if not fiches:
        raise ErreurDImport(
            "Aucune fiche d'entrée trouvée : l'archive doit contenir data/items/*.yaml."
        )
    return fiches, lots


def _lire_yaml(nom, contenu):
    try:
        donnees = yaml.safe_load(contenu.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as erreur:
        raise ErreurDImport(f"{nom} : fichier YAML illisible ({erreur}).") from erreur
    if not isinstance(donnees, dict):
        raise ErreurDImport(f"{nom} : le fichier devrait décrire un objet YAML.")
    return donnees


# --- Conversion ---------------------------------------------------------------


def correspondance(table, code, fichier, champ):
    """Le code du modèle qui correspond à ``code`` ; erreur claire s'il n'y en a pas."""
    try:
        return table[code]
    except (KeyError, TypeError):
        raise ErreurDImport(
            f"{fichier}, champ « {champ} » : code inconnu « {code} »."
        ) from None


def _requis(donnees, cle, fichier):
    if cle not in donnees:
        raise ErreurDImport(f"{fichier} : le champ « {cle} » manque.")
    return donnees[cle]


def valeurs_de_l_entree(fiche, fichier):
    """Les champs d'``Entree`` tirés d'une fiche (sans les thèmes)."""
    niveau = _requis(fiche, "cefr", fichier)
    valeurs = {
        "slug": _requis(fiche, "id", fichier),
        "vedette": _requis(fiche, "headword", fichier),
        "precision": PRECISIONS.get(
            fiche.get("sense_label", ""), fiche.get("sense_label", "")
        ),
        "type_entree": correspondance(
            TYPES_ENTREE, _requis(fiche, "kind", fichier), fichier, "kind"
        ),
        "nature": correspondance(
            NATURES, _requis(fiche, "pos", fichier), fichier, "pos"
        ),
        "genre": (
            correspondance(GENRES, fiche["gender"], fichier, "gender")
            if "gender" in fiche
            else ""
        ),
        "api": fiche.get("ipa", ""),
        "niveau": niveau,
        "registre": _requis(fiche, "register", fichier),
        "frequence": correspondance(
            FREQUENCES, _requis(fiche, "frequency", fichier), fichier, "frequency"
        ),
        "regions": list(fiche.get("regions", [])),
        "formes": list(fiche.get("forms", [])),
    }
    definition = fiche.get("definition_fr", "")
    if definition:
        if not isinstance(niveau, str) or niveau.lower() not in m.NIVEAUX_EN_MINUSCULES:
            raise ErreurDImport(
                f"{fichier}, champ « cefr » : code inconnu « {niveau} »."
            )
        valeurs[f"sens_{niveau.lower()}"] = definition
    return valeurs


def valeurs_du_piege(piege, fichier):
    """Les champs de ``Piege`` tirés d'un piège (« gotcha ») d'une fiche."""
    type_piege = correspondance(
        TYPES_PIEGE, _requis(piege, "type", fichier), fichier, "gotchas.type"
    )
    selon_la_langue = (
        type_piege in PIEGES_SELON_LA_LANGUE and piege.get("l1") == LANGUE_DES_DONNEES
    )
    return {
        "type_piege": type_piege,
        "concerne": list(_requis(piege, "affects", fichier)),
        "gravite": correspondance(
            GRAVITES, _requis(piege, "severity", fichier), fichier, "gotchas.severity"
        ),
        "langue_apprenant": LANGUE_DES_DONNEES if selon_la_langue else "",
        "declencheur": piege.get("trigger", ""),
        "incorrect": piege.get("wrong", ""),
        "correct": piege.get("right", ""),
    }


# --- Import -------------------------------------------------------------------


def compte_d_import():
    """Le compte système auquel tout est attribué. Il ne peut pas se connecter."""
    compte, cree = get_user_model().objects.get_or_create(
        username=NOM_DU_COMPTE, defaults={"is_active": False}
    )
    if cree:
        compte.set_unusable_password()
        compte.save(update_fields=["password"])
    return compte


class Import:
    """Un passage de l'import, dans une seule transaction."""

    def __init__(self, fiches, lots):
        self.fiches = fiches
        self.lots = lots
        self.bilan = Bilan()
        self.compte = compte_d_import()
        self.themes = {}
        # Les entrées de départ (déjà là ou créées maintenant), par slug.
        self.entrees = {
            entree.slug: entree
            for entree in m.Entree.objects.filter(genere_par_ia=True)
        }
        self.nouvelles_entrees = set()
        self.slugs_de_l_archive = {
            fiche.get("id"): fichier for fichier, fiche in self.fiches
        }

    def lancer(self):
        for fichier, fiche in self.fiches:
            self.importer_l_entree(fiche, fichier)
        for fichier, fiche in self.fiches:
            self.importer_les_liens(fiche, fichier)
        ordres = collections.Counter()
        for fichier, lot in self.lots:
            for phrase in _requis(lot, "sentences", fichier):
                self.importer_la_phrase(phrase, fichier, ordres)
        return self.bilan

    def enregistrer(self, objet, quoi, fichier):
        """Valide puis enregistre un objet de départ, attribué au compte d'import."""
        objet.genere_par_ia = True
        if isinstance(objet, m.Contenu):
            objet.ajoute_par = self.compte
        objet._history_user = self.compte
        try:
            objet.full_clean()
            objet.save()
        except ValidationError as erreur:
            raise ErreurDImport(f"{fichier} ({quoi}) : {_messages(erreur)}") from erreur
        self.bilan.crees[type(objet).__name__] += 1
        return objet

    def theme(self, sujet, fichier):
        slug, nom = correspondance(THEMES, sujet, fichier, "topics")
        if slug not in self.themes:
            theme = m.Theme.objects.filter(slug=slug).first()
            if theme is None:
                theme = self.enregistrer(m.Theme(slug=slug, nom=nom), slug, fichier)
            self.themes[slug] = theme
        return self.themes[slug]

    def importer_l_entree(self, fiche, fichier):
        valeurs = valeurs_de_l_entree(fiche, fichier)
        slug = valeurs["slug"]
        if m.Entree.objects.filter(slug=slug).exists():
            self.bilan.entrees_deja_presentes.append(slug)
            return
        entree = self.enregistrer(m.Entree(**valeurs), slug, fichier)
        entree.themes.set(
            [self.theme(sujet, fichier) for sujet in fiche.get("topics", [])]
        )
        self.enregistrer(
            m.EntreeTraduction(
                entree=entree,
                langue=LANGUE_DES_DONNEES,
                sens=_requis(fiche, "gloss_en", fichier),
                sens_litteral=fiche.get("literal_en", ""),
            ),
            f"{slug}, traduction",
            fichier,
        )
        for numero, donnees in enumerate(_requis(fiche, "gotchas", fichier), start=1):
            quoi = f"{slug}, piège {numero}"
            piege = self.enregistrer(
                m.Piege(entree=entree, **valeurs_du_piege(donnees, fichier)),
                quoi,
                fichier,
            )
            self.enregistrer(
                m.PiegeTraduction(
                    piege=piege,
                    langue=LANGUE_DES_DONNEES,
                    explication=_requis(donnees, "note_en", fichier),
                ),
                f"{quoi}, traduction",
                fichier,
            )
        self.entrees[slug] = entree
        self.nouvelles_entrees.add(slug)

    def entree_de_depart(self, slug, fichier, champ):
        """L'entrée de départ ``slug`` ; None si une entrée faite à la main a ce slug."""
        if slug not in self.slugs_de_l_archive:
            raise ErreurDImport(
                f"{fichier}, champ « {champ} » : aucune fiche ne porte l'identifiant "
                f"« {slug} »."
            )
        return self.entrees.get(slug)

    def importer_les_liens(self, fiche, fichier):
        source = self.entrees.get(fiche["id"])
        for lien in fiche.get("related", []):
            type_lien = correspondance(
                TYPES_LIEN, _requis(lien, "type", fichier), fichier, "related.type"
            )
            cible = self.entree_de_depart(
                _requis(lien, "target", fichier), fichier, "related.target"
            )
            if (
                source is None
                or cible is None
                or {source.slug, cible.slug}.isdisjoint(self.nouvelles_entrees)
                or m.LienEntree.objects.filter(
                    entree=source, cible=cible, type_lien=type_lien
                ).exists()
            ):
                continue
            self.enregistrer(
                m.LienEntree(entree=source, cible=cible, type_lien=type_lien),
                f"lien {source.slug} → {cible.slug}",
                fichier,
            )

    def importer_la_phrase(self, donnees, fichier, ordres):
        identifiant = donnees.get("id", "?")
        texte = _requis(donnees, "fr", fichier)
        exemple = m.Exemple.objects.filter(genere_par_ia=True, phrase=texte).first()
        nouvel_exemple = exemple is None
        if nouvel_exemple:
            exemple = self.enregistrer(
                m.Exemple(phrase=texte, niveau=_requis(donnees, "cefr", fichier)),
                f"phrase {identifiant}",
                fichier,
            )
            if donnees.get("en"):
                self.enregistrer(
                    m.ExempleTraduction(
                        exemple=exemple,
                        langue=LANGUE_DES_DONNEES,
                        traduction=donnees["en"],
                    ),
                    f"phrase {identifiant}, traduction",
                    fichier,
                )
        for etiquette in donnees.get("tags", []):
            slug = _requis(etiquette, "item", fichier)
            if etiquette.get("occurrence", 1) != 1:
                raise ErreurDImport(
                    f"{fichier}, phrase {identifiant} : « occurrence » n'est pas prise en "
                    "charge (le surlignage vise la première occurrence)."
                )
            ordres[slug] += 1
            entree = self.entree_de_depart(slug, fichier, f"phrase {identifiant}, tags")
            if (
                entree is None
                or not (nouvel_exemple or slug in self.nouvelles_entrees)
                or m.ExempleEntree.objects.filter(
                    exemple=exemple, entree=entree
                ).exists()
            ):
                continue
            self.enregistrer(
                m.ExempleEntree(
                    exemple=exemple,
                    entree=entree,
                    surlignage=_requis(etiquette, "text", fichier),
                    ordre=ordres[slug],
                ),
                f"phrase {identifiant}, entrée {slug}",
                fichier,
            )


def _messages(erreur):
    if hasattr(erreur, "message_dict"):
        return " ".join(
            f"{champ} : {' '.join(str(message) for message in messages)}"
            for champ, messages in erreur.message_dict.items()
        )
    return " ".join(str(message) for message in erreur.messages)


def importer(chemin):
    """Importe l'archive (zip ou dossier) en une seule transaction et renvoie le bilan."""
    fiches, lots = lire_archive(chemin)
    with transaction.atomic():
        return Import(fiches, lots).lancer()

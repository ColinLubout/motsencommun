"""Vocabulaires du lexique : chaque code stocké en base, avec son libellé en français.

Les codes sont en ASCII et ne changent jamais : ils font partie des
téléchargements. Les libellés, eux, sont des textes d'interface traduisibles.
"""

from django.conf.locale import LANG_INFO
from django.db import models
from django.utils.translation import gettext_lazy as _


class Niveau(models.TextChoices):
    A1 = "A1", "A1"
    A2 = "A2", "A2"
    B1 = "B1", "B1"
    B2 = "B2", "B2"
    C1 = "C1", "C1"
    C2 = "C2", "C2"


#: Les niveaux, du plus simple au plus difficile.
NIVEAUX = [niveau.value for niveau in Niveau]


class TypeEntree(models.TextChoices):
    MOT = "mot", _("Mot")
    EXPRESSION = "expression", _("Expression")
    CONSTRUCTION = "construction", _("Construction")


class Nature(models.TextChoices):
    NOM = "nom", _("Nom")
    VERBE = "verbe", _("Verbe")
    ADJECTIF = "adjectif", _("Adjectif")
    ADVERBE = "adverbe", _("Adverbe")
    PREPOSITION = "preposition", _("Préposition")
    CONJONCTION = "conjonction", _("Conjonction")
    PRONOM = "pronom", _("Pronom")
    DETERMINANT = "determinant", _("Déterminant")
    NUMERAL = "numeral", _("Numéral")
    INTERJECTION = "interjection", _("Interjection")
    LOCUTION_VERBALE = "locution_verbale", _("Locution verbale")
    LOCUTION_NOMINALE = "locution_nominale", _("Locution nominale")
    LOCUTION_ADJECTIVALE = "locution_adjectivale", _("Locution adjectivale")
    LOCUTION_ADVERBIALE = "locution_adverbiale", _("Locution adverbiale")
    LOCUTION_PREPOSITIONNELLE = (
        "locution_prepositionnelle",
        _("Locution prépositionnelle"),
    )
    LOCUTION_CONJONCTIVE = "locution_conjonctive", _("Locution conjonctive")
    PHRASE = "phrase", _("Phrase")


class Genre(models.TextChoices):
    MASCULIN = "masculin", _("Masculin")
    FEMININ = "feminin", _("Féminin")
    EPICENE = "epicene", _("Épicène")
    PLURIEL_SEULEMENT = "pluriel_seulement", _("Pluriel seulement")


class Registre(models.TextChoices):
    SOUTENU = "soutenu", _("Soutenu")
    COURANT = "courant", _("Courant")
    FAMILIER = "familier", _("Familier")
    TRES_FAMILIER = "tres_familier", _("Très familier")
    VULGAIRE = "vulgaire", _("Vulgaire")
    ARGOT = "argot", _("Argot")


class Frequence(models.TextChoices):
    TRES_COURANTE = "tres_courante", _("Très courante")
    COURANTE = "courante", _("Courante")
    PEU_COURANTE = "peu_courante", _("Peu courante")
    RARE = "rare", _("Rare")


class Region(models.TextChoices):
    FR = "FR", _("France")
    BE = "BE", _("Belgique")
    CH = "CH", _("Suisse")
    CA_QC = "CA_QC", _("Québec")
    LU = "LU", _("Luxembourg")
    AF = "AF", _("Afrique francophone")


class Concerne(models.TextChoices):
    COMPREHENSION = "comprehension", _("Compréhension")
    PRODUCTION = "production", _("Production")


class Gravite(models.TextChoices):
    FAIBLE = "faible", _("Faible")
    MOYENNE = "moyenne", _("Moyenne")
    ELEVEE = "elevee", _("Élevée")


class TypeLien(models.TextChoices):
    VOIR_AUSSI = "voir_aussi", _("Voir aussi")
    CONTRAIRE = "contraire", _("Contraire")
    A_NE_PAS_CONFONDRE = "a_ne_pas_confondre", _("À ne pas confondre")
    VARIANTE = "variante", _("Variante")


class Statut(models.TextChoices):
    BROUILLON = "brouillon", _("Brouillon")
    EN_RELECTURE = "en_relecture", _("En relecture")
    RELU = "relu", _("Relu")
    VALIDE = "valide", _("Validé")
    REFUSE = "refuse", _("Refusé")
    RETIRE = "retire", _("Retiré")


#: Les statuts visibles sur le site public.
STATUTS_PUBLICS = [Statut.RELU, Statut.VALIDE]


class Decision(models.TextChoices):
    APPROUVE = "approuve", _("Approuvé")
    REFUSE = "refuse", _("Refusé")


class TypePiege(models.TextChoices):
    SENS_FIGURE = "sens_figure", _("Sens figuré")
    FAUX_AMI = "faux_ami", _("Faux ami")
    FAUX_AMI_PARTIEL = "faux_ami_partiel", _("Faux ami partiel")
    CONNOTATION = "connotation", _("Connotation")
    CALQUE = "calque", _("Calque")
    CONSTRUCTION_INVERSEE = "construction_inversee", _("Construction inversée")
    SENS_SELON_POSITION = "sens_selon_position", _("Sens selon la position")
    SENS_SELON_GENRE = "sens_selon_genre", _("Sens selon le genre")
    POLARITE = "polarite", _("Polarité")
    PRONONCIATION = "prononciation", _("Prononciation")
    MODE_IMPOSE = "mode_impose", _("Mode imposé")
    PREPOSITION = "preposition", _("Préposition")
    FORME_FIGEE = "forme_figee", _("Forme figée")
    CONFUSION_POSSIBLE = "confusion_possible", _("Confusion possible")
    FORME_IRREGULIERE = "forme_irreguliere", _("Forme irrégulière")
    REGISTRE = "registre", _("Registre")
    REGIONAL = "regional", _("Régional")
    PRAGMATIQUE = "pragmatique", _("Pragmatique")


# Les langues : les codes ISO 639-1 (deux lettres) que Django connaît, avec leur
# nom traduit (« Anglais », « Polonais »…). Django sait aussi lesquelles
# s'écrivent de droite à gauche, ce qui servira pour l'attribut dir.
Langue = models.TextChoices(
    "Langue",
    sorted(
        (
            (code.upper(), (code, _(infos["name"])))
            for code, infos in LANG_INFO.items()
            if len(code) == 2 and "name" in infos
        ),
    ),
)

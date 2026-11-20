"""Modèles du lexique : entrées, pièges, exemples, thèmes, traductions et relectures.

Règles de relecture appliquées ici, quel que soit le chemin (administration,
commande, shell) :

- « relu » et « validé » ne se décident que par des relectures : la première
  approbation donne « relu », celle d'une deuxième personne « validé » ;
- personne ne relit un contenu qu'il a ajouté ou modifié ;
- modifier le texte d'un contenu relu le renvoie en relecture, et les
  approbations antérieures ne comptent plus.
"""

import re

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from lexique import vocabulaire as v
from lexique.champs import ListeJSON
from lexique.recherche import (
    apostrophes_droites,
    cle_de_tri_de_l_entree,
    nfc,
    recherche_de_l_entree,
    recherche_de_la_traduction,
)

NIVEAUX_EN_MINUSCULES = [niveau.lower() for niveau in v.NIVEAUX]

# « à qqn », « de qqch »… : retirés de la vedette pour former le slug.
EMPLACEMENTS = re.compile(
    r"\b(?:(?:à|a|de|d'|d’|en|pour|sur|avec|chez|contre)\s+)?(?:qqn|qqch)\b",
    re.IGNORECASE,
)
LIGATURES = str.maketrans({"œ": "oe", "Œ": "OE", "æ": "ae", "Æ": "AE"})


def slug_depuis(*textes):
    """Slug ASCII tiré de la vedette (et de la précision), sans « qqn » ni « qqch »."""
    texte = " ".join(t for t in textes if t)
    texte = EMPLACEMENTS.sub(" ", texte).translate(LIGATURES)
    return slugify(texte)


# --- Bases communes -----------------------------------------------------------


class TextesNormalises(models.Model):
    """Tout texte enregistré est en Unicode NFC (PRD, « Every alphabet »).

    La normalisation a lieu à la validation (``clean_fields``, donc avant
    ``clean()`` et ses vérifications) et à l'enregistrement. Un ``save()`` qui
    vérifie quelque chose avant d'appeler ``super().save()`` normalise d'abord.
    """

    #: Champs cherchés ou surlignés : leurs apostrophes typographiques (’) deviennent
    #: droites ('), pour que recherches et surlignages concordent.
    CHAMPS_A_APOSTROPHES_DROITES = frozenset()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.normaliser_les_textes()
        super().save(*args, **kwargs)

    def clean_fields(self, exclude=None):
        self.normaliser_les_textes()
        super().clean_fields(exclude=exclude)

    def normaliser_les_textes(self):
        for champ in self._meta.concrete_fields:
            valeur = getattr(self, champ.attname)
            if isinstance(valeur, str):
                setattr(self, champ.attname, self._normaliser(champ.name, valeur))
            elif isinstance(champ, ListeJSON) and isinstance(valeur, list):
                setattr(
                    self,
                    champ.attname,
                    [
                        self._normaliser(champ.name, element)
                        if isinstance(element, str)
                        else element
                        for element in valeur
                    ],
                )

    def _normaliser(self, nom_du_champ, texte):
        texte = nfc(texte)
        if nom_du_champ in self.CHAMPS_A_APOSTROPHES_DROITES:
            texte = apostrophes_droites(texte)
        return texte


class MarqueIA(TextesNormalises):
    """Marque les données de départ, rédigées par une IA, qui ne servent qu'aux essais."""

    genere_par_ia = models.BooleanField(
        _("généré par IA"),
        default=False,
        editable=False,
        help_text=_("Donnée de départ rédigée par une IA, pour les essais seulement."),
    )

    class Meta:
        abstract = True


class Contenu(MarqueIA):
    """Champs et règles communs aux contenus relus : entrées, pièges, exemples, traductions."""

    cree_le = models.DateTimeField(_("créé le"), auto_now_add=True)
    modifie_le = models.DateTimeField(_("modifié le"), auto_now=True)
    texte_modifie_le = models.DateTimeField(
        _("texte modifié le"),
        default=timezone.now,
        editable=False,
        help_text=_("Seules les approbations postérieures comptent."),
    )
    ajoute_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("ajouté par"),
    )
    statut = models.CharField(
        _("statut"),
        max_length=20,
        choices=v.Statut.choices,
        default=v.Statut.BROUILLON,
        db_index=True,
    )
    relectures = GenericRelation(
        "Relecture", content_type_field="type_contenu", object_id_field="id_contenu"
    )

    #: Champs qui ne font pas partie du texte relu.
    CHAMPS_HORS_TEXTE = frozenset(
        {
            "id",
            "cree_le",
            "modifie_le",
            "texte_modifie_le",
            "ajoute_par",
            "statut",
            "genere_par_ia",
            # Calculés à partir du texte, pour chercher et trier.
            "recherche",
            "cle_de_tri",
        }
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Normaliser avant de comparer avec la version enregistrée : un texte
        # identique, saisi sous une autre forme Unicode, n'est pas une modification.
        self.normaliser_les_textes()
        with transaction.atomic():
            ancien = type(self).objects.filter(pk=self.pk).first() if self.pk else None
            if ancien is not None and any(
                getattr(ancien, champ) != getattr(self, champ)
                for champ in self.champs_du_texte()
            ):
                self.texte_modifie_le = timezone.now()
                if update_fields := kwargs.get("update_fields"):
                    kwargs["update_fields"] = {
                        *update_fields,
                        "texte_modifie_le",
                        "statut",
                    }
                # Le texte d'un contenu public a changé : il repasse en relecture.
                if ancien.statut in v.STATUTS_PUBLICS and self.statut == ancien.statut:
                    self.statut = v.Statut.EN_RELECTURE
            self.verifier_statut()
            super().save(*args, **kwargs)

    def champs_du_texte(self):
        """Noms (attname) des champs qui forment le texte relu."""
        return [
            champ.attname
            for champ in self._meta.concrete_fields
            if champ.name not in self.CHAMPS_HORS_TEXTE
        ]

    def langue_du_contenu(self):
        """Langue dans laquelle le contenu est écrit : celle de son relecteur."""
        return "fr"

    def editeurs(self):
        """Identifiants des personnes qui ont ajouté ou modifié le texte de ce contenu."""
        editeurs = {self.ajoute_par_id}
        if self.pk is None:
            return editeurs
        champs = self.champs_du_texte()
        precedente = None
        for version in self.history.order_by("history_date", "history_id"):
            texte_change = precedente is None or any(
                getattr(version, champ) != getattr(precedente, champ)
                for champ in champs
            )
            if texte_change and version.history_user_id is not None:
                editeurs.add(version.history_user_id)
            precedente = version
        return editeurs

    def approbateurs(self):
        """Personnes qui ont approuvé la version actuelle du texte, sans en être éditrices."""
        if self.pk is None:
            return set()
        editeurs = self.editeurs()
        relectures = self.relectures.filter(
            decision=v.Decision.APPROUVE, date__gte=self.texte_modifie_le
        )
        return {r.relecteur_id for r in relectures} - editeurs

    def prerequis_d_approbation(self):
        """Ce qui manque pour pouvoir approuver ce contenu (liste de messages)."""
        return []

    def verifier_statut(self):
        """Refuse un statut que les relectures ne justifient pas."""
        if self.statut in (v.Statut.RELU, v.Statut.VALIDE):
            requis = 1 if self.statut == v.Statut.RELU else 2
            if len(self.approbateurs()) < requis:
                raise ValidationError(
                    {
                        "statut": _(
                            "« %(statut)s » ne se choisit pas : ce statut vient des "
                            "relectures (une approbation pour « relu », deux pour "
                            "« validé », par des personnes qui n'ont ni ajouté ni "
                            "modifié ce contenu)."
                        )
                        % {"statut": self.get_statut_display()}
                    }
                )
            manques = self.prerequis_d_approbation()
            if manques:
                raise ValidationError(manques)
        elif self.statut == v.Statut.REFUSE and (
            self.pk is None
            or not self.relectures.filter(decision=v.Decision.REFUSE).exists()
        ):
            raise ValidationError(
                {"statut": _("« Refusé » vient d'une relecture qui refuse ce contenu.")}
            )


# --- Thèmes -------------------------------------------------------------------


class Theme(MarqueIA):
    slug = models.SlugField(_("slug"), max_length=80, unique=True)
    nom = models.CharField(_("nom"), max_length=100)
    history = HistoricalRecords()

    class Meta:
        ordering = ["nom"]
        verbose_name = _("thème")
        verbose_name_plural = _("thèmes")

    def __str__(self):
        return self.nom


class ThemeTraduction(MarqueIA):
    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name="traductions",
        verbose_name=_("thème"),
    )
    langue = models.CharField(_("langue"), max_length=8, choices=v.Langue.choices)
    nom = models.CharField(_("nom"), max_length=100)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("traduction de thème")
        verbose_name_plural = _("traductions de thèmes")
        constraints = [
            models.UniqueConstraint(
                fields=["theme", "langue"], name="themetraduction_unique"
            )
        ]

    def __str__(self):
        return f"{self.theme} ({self.langue})"

    def clean(self):
        verifier_langue_de_traduction(self.langue)


# --- Entrées ------------------------------------------------------------------


class Entree(Contenu):
    slug = models.SlugField(
        _("slug"),
        max_length=120,
        unique=True,
        blank=True,
        help_text=_(
            "Adresse permanente de la fiche, tirée de la vedette si on la laisse vide. "
            "Elle ne change plus ensuite."
        ),
    )
    vedette = models.CharField(_("vedette"), max_length=200)
    precision = models.CharField(_("précision"), max_length=200, blank=True)
    type_entree = models.CharField(
        _("type d'entrée"), max_length=20, choices=v.TypeEntree.choices
    )
    nature = models.CharField(_("nature"), max_length=30, choices=v.Nature.choices)
    genre = models.CharField(
        _("genre"), max_length=20, choices=v.Genre.choices, blank=True
    )
    api = models.CharField(_("prononciation (API)"), max_length=200, blank=True)
    sens_a1 = models.TextField(_("sens (A1)"), blank=True)
    sens_a2 = models.TextField(_("sens (A2)"), blank=True)
    sens_b1 = models.TextField(_("sens (B1)"), blank=True)
    sens_b2 = models.TextField(_("sens (B2)"), blank=True)
    sens_c1 = models.TextField(_("sens (C1)"), blank=True)
    sens_c2 = models.TextField(_("sens (C2)"), blank=True)
    sens_litteral = models.TextField(_("sens littéral"), blank=True)
    niveau = models.CharField(_("niveau"), max_length=2, choices=v.Niveau.choices)
    registre = models.CharField(
        _("registre"), max_length=20, choices=v.Registre.choices
    )
    frequence = models.CharField(
        _("fréquence"), max_length=20, choices=v.Frequence.choices
    )
    regions = ListeJSON(
        _("régions"),
        vocabulaire="Region",
        blank=True,
        help_text=_("Aucune région cochée : partout."),
    )
    themes = models.ManyToManyField(
        Theme, blank=True, related_name="entrees", verbose_name=_("thèmes")
    )
    formes = ListeJSON(
        _("formes"),
        blank=True,
        help_text=_(
            "Graphies à chercher, une par ligne : j'en ai marre, t'en as marre…"
        ),
    )
    liens = models.ManyToManyField(
        "self",
        through="LienEntree",
        symmetrical=False,
        blank=True,
        related_name="+",
        verbose_name=_("liens"),
    )
    recherche = models.TextField(
        _("texte de recherche"),
        blank=True,
        default="",
        editable=False,
        help_text=_("Vedette, formes et sens, sans casse ni accents, pour chercher."),
    )
    cle_de_tri = models.BinaryField(
        _("clé de tri"),
        blank=True,
        default=b"",
        editable=False,
        help_text=_(
            "Vedette puis précision, dans l'ordre alphabétique français (ICU)."
        ),
    )
    history = HistoricalRecords(
        m2m_fields=[themes], excluded_fields=["recherche", "cle_de_tri"]
    )

    CHAMPS_A_APOSTROPHES_DROITES = frozenset({"formes"})

    class Meta:
        ordering = ["cle_de_tri"]
        verbose_name = _("entrée")
        verbose_name_plural = _("entrées")

    def __str__(self):
        return f"{self.vedette} ({self.precision})" if self.precision else self.vedette

    def save(self, *args, **kwargs):
        self.normaliser_les_textes()
        if not self.slug:
            self.slug = slug_depuis(self.vedette, self.precision)
        self.verifier_slug()
        self.recherche = recherche_de_l_entree(self)
        self.cle_de_tri = cle_de_tri_de_l_entree(self)
        if update_fields := kwargs.get("update_fields"):
            kwargs["update_fields"] = {*update_fields, "recherche", "cle_de_tri"}
        super().save(*args, **kwargs)

    def sens(self):
        """Les versions du sens qui sont remplies, par niveau : {"B1": "…"}."""
        versions = {n: getattr(self, f"sens_{n.lower()}") for n in v.NIVEAUX}
        return {niveau: texte for niveau, texte in versions.items() if texte.strip()}

    def prerequis_d_approbation(self):
        manques = []
        if not self.sens():
            manques.append(_("Écrivez le sens en français à au moins un niveau."))
        pieges_sans_explication = [
            piege
            for piege in self.pieges.exclude(
                statut__in=[v.Statut.REFUSE, v.Statut.RETIRE]
            )
            if not piege.explications()
        ]
        if pieges_sans_explication:
            manques.append(
                _("Chaque piège de l'entrée doit avoir une explication en français.")
            )
        return manques

    def clean(self):
        if not self.slug:
            self.slug = slug_depuis(self.vedette, self.precision)
            if not self.slug:
                raise ValidationError(
                    {"slug": _("Indiquez un slug : la vedette n'en donne pas.")}
                )
        self.verifier_slug()

    def verifier_slug(self):
        if self.pk is not None:
            ancien = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("slug", flat=True)
                .first()
            )
            if ancien is not None and ancien != self.slug:
                raise ValidationError(
                    {
                        "slug": _(
                            "Le slug d'une entrée ne change jamais, pour que les liens "
                            "vers sa fiche restent valables."
                        )
                    }
                )
        if type(self).objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError(
                {
                    "slug": _(
                        "Une autre entrée a déjà le slug « %(slug)s » : "
                        "remplissez la précision ou choisissez un autre slug."
                    )
                    % {"slug": self.slug}
                }
            )


class LienEntree(MarqueIA):
    entree = models.ForeignKey(
        Entree,
        on_delete=models.CASCADE,
        related_name="liens_sortants",
        verbose_name=_("entrée"),
    )
    cible = models.ForeignKey(
        Entree,
        on_delete=models.CASCADE,
        related_name="liens_entrants",
        verbose_name=_("entrée liée"),
    )
    type_lien = models.CharField(
        _("type de lien"), max_length=30, choices=v.TypeLien.choices
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("lien entre entrées")
        verbose_name_plural = _("liens entre entrées")
        constraints = [
            models.UniqueConstraint(
                fields=["entree", "cible", "type_lien"], name="lienentree_unique"
            ),
            models.CheckConstraint(
                condition=~models.Q(entree=models.F("cible")),
                name="lienentree_pas_vers_soi",
            ),
        ]

    def __str__(self):
        return f"{self.entree} → {self.cible} ({self.get_type_lien_display()})"

    def clean(self):
        if self.entree_id and self.entree_id == self.cible_id:
            raise ValidationError(
                {"cible": _("Une entrée ne peut pas être liée à elle-même.")}
            )


# --- Pièges -------------------------------------------------------------------


class Piege(Contenu):
    entree = models.ForeignKey(
        Entree,
        on_delete=models.CASCADE,
        related_name="pieges",
        verbose_name=_("entrée"),
    )
    type_piege = models.CharField(
        _("type de piège"), max_length=30, choices=v.TypePiege.choices
    )
    concerne = ListeJSON(_("concerne"), vocabulaire="Concerne")
    gravite = models.CharField(_("gravité"), max_length=10, choices=v.Gravite.choices)
    langue_apprenant = models.CharField(
        _("langue de l'apprenant"),
        max_length=8,
        choices=v.Langue.choices,
        blank=True,
        help_text=_(
            "Seulement si le piège dépend de la langue de l'apprenant (faux amis…)."
        ),
    )
    declencheur = models.CharField(_("déclencheur"), max_length=200, blank=True)
    explication_a1 = models.TextField(_("explication (A1)"), blank=True)
    explication_a2 = models.TextField(_("explication (A2)"), blank=True)
    explication_b1 = models.TextField(_("explication (B1)"), blank=True)
    explication_b2 = models.TextField(_("explication (B2)"), blank=True)
    explication_c1 = models.TextField(_("explication (C1)"), blank=True)
    explication_c2 = models.TextField(_("explication (C2)"), blank=True)
    incorrect = models.TextField(_("incorrect"), blank=True)
    correct = models.TextField(_("correct"), blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["entree", "id"]
        verbose_name = _("piège")
        verbose_name_plural = _("pièges")

    def __str__(self):
        return f"{self.entree} : {self.get_type_piege_display()}"

    def explications(self):
        """Les versions de l'explication qui sont remplies, par niveau."""
        versions = {n: getattr(self, f"explication_{n.lower()}") for n in v.NIVEAUX}
        return {niveau: texte for niveau, texte in versions.items() if texte.strip()}

    def prerequis_d_approbation(self):
        if not self.explications():
            return [_("Écrivez l'explication en français à au moins un niveau.")]
        return []


# --- Exemples -----------------------------------------------------------------


class Exemple(Contenu):
    phrase = models.TextField(_("phrase"))
    niveau = models.CharField(_("niveau"), max_length=2, choices=v.Niveau.choices)
    entrees = models.ManyToManyField(
        Entree,
        through="ExempleEntree",
        blank=True,
        related_name="exemples",
        verbose_name=_("entrées"),
    )
    history = HistoricalRecords()

    # Décidé le 20 novembre 2026 : les phrases aussi, pour que surlignages et
    # phrases concordent caractère pour caractère.
    CHAMPS_A_APOSTROPHES_DROITES = frozenset({"phrase"})

    class Meta:
        ordering = ["id"]
        verbose_name = _("exemple")
        verbose_name_plural = _("exemples")

    def __str__(self):
        return self.phrase

    def save(self, *args, **kwargs):
        # Pas de vérification dans clean() : dans un formulaire, la phrase et ses
        # surlignages changent ensemble, et chaque surlignage se vérifie lui-même
        # contre la nouvelle phrase. Ici, au moment d'enregistrer, tout doit concorder.
        self.normaliser_les_textes()
        self.verifier_surlignages()
        super().save(*args, **kwargs)

    def prerequis_d_approbation(self):
        if self.pk is None or not self.liens_entrees.exists():
            return [_("Rattachez l'exemple à au moins une entrée.")]
        return []

    def verifier_surlignages(self):
        """Chaque surlignage de l'exemple doit apparaître tel quel dans la phrase."""
        if self.pk is None:
            return
        for lien in self.liens_entrees.all():
            if lien.surlignage not in self.phrase:
                raise ValidationError(
                    {
                        "phrase": _(
                            "La phrase ne contient plus « %(surlignage)s », le surlignage "
                            "de l'entrée « %(entree)s ». Modifiez aussi ce surlignage."
                        )
                        % {"surlignage": lien.surlignage, "entree": lien.entree}
                    }
                )


class ExempleEntree(MarqueIA):
    """Rattache un exemple à une entrée qu'il illustre, avec les mots à surligner."""

    exemple = models.ForeignKey(
        Exemple,
        on_delete=models.CASCADE,
        related_name="liens_entrees",
        verbose_name=_("exemple"),
    )
    entree = models.ForeignKey(
        Entree,
        on_delete=models.CASCADE,
        related_name="liens_exemples",
        verbose_name=_("entrée"),
    )
    surlignage = models.CharField(
        _("surlignage"),
        max_length=255,
        help_text=_("Les mots exacts de la phrase à mettre en évidence."),
    )
    ordre = models.PositiveSmallIntegerField(_("ordre"), default=0)
    history = HistoricalRecords()

    CHAMPS_A_APOSTROPHES_DROITES = frozenset({"surlignage"})

    class Meta:
        ordering = ["ordre", "id"]
        verbose_name = _("exemple d'une entrée")
        verbose_name_plural = _("exemples des entrées")
        constraints = [
            models.UniqueConstraint(
                fields=["exemple", "entree"], name="exempleentree_unique"
            )
        ]

    def __str__(self):
        return f"{self.entree} : {self.surlignage}"

    def save(self, *args, **kwargs):
        self.normaliser_les_textes()
        self.verifier_surlignage(self.exemple.phrase)
        super().save(*args, **kwargs)

    def clean(self):
        try:
            phrase = self.exemple.phrase
        except Exemple.DoesNotExist:
            return  # l'exemple manque : le formulaire le signale déjà
        self.verifier_surlignage(phrase)

    def verifier_surlignage(self, phrase):
        # La phrase d'un formulaire n'est pas forcément encore normalisée.
        if self.surlignage not in apostrophes_droites(nfc(phrase)):
            raise ValidationError(
                {
                    "surlignage": _(
                        "« %(surlignage)s » n'apparaît pas dans la phrase. Le surlignage "
                        "reprend exactement des mots de la phrase, avec les mêmes "
                        "majuscules et la même ponctuation."
                    )
                    % {"surlignage": self.surlignage}
                }
            )


# --- Traductions --------------------------------------------------------------


def verifier_langue_de_traduction(langue):
    if langue == "fr":
        raise ValidationError(
            {
                "langue": _(
                    "Le français est la langue d'origine : traduisez vers une autre langue."
                )
            }
        )


class Traduction(Contenu):
    langue = models.CharField(_("langue"), max_length=8, choices=v.Langue.choices)

    class Meta:
        abstract = True

    def langue_du_contenu(self):
        return self.langue

    def clean(self):
        verifier_langue_de_traduction(self.langue)


class EntreeTraduction(Traduction):
    entree = models.ForeignKey(
        Entree,
        on_delete=models.CASCADE,
        related_name="traductions",
        verbose_name=_("entrée"),
    )
    sens = models.TextField(_("sens"), blank=True)
    sens_litteral = models.TextField(_("sens littéral"), blank=True)
    recherche = models.TextField(
        _("texte de recherche"),
        blank=True,
        default="",
        editable=False,
        help_text=_("Le sens sans casse, pour chercher dans cette langue."),
    )
    history = HistoricalRecords(excluded_fields=["recherche"])

    class Meta:
        verbose_name = _("traduction d'entrée")
        verbose_name_plural = _("traductions d'entrées")
        constraints = [
            models.UniqueConstraint(
                fields=["entree", "langue"], name="entreetraduction_unique"
            )
        ]

    def __str__(self):
        return f"{self.entree} ({self.langue})"

    def save(self, *args, **kwargs):
        self.normaliser_les_textes()
        self.recherche = recherche_de_la_traduction(self)
        if update_fields := kwargs.get("update_fields"):
            kwargs["update_fields"] = {*update_fields, "recherche"}
        super().save(*args, **kwargs)

    def prerequis_d_approbation(self):
        return [] if self.sens.strip() else [_("Écrivez le sens dans cette langue.")]


class PiegeTraduction(Traduction):
    piege = models.ForeignKey(
        Piege,
        on_delete=models.CASCADE,
        related_name="traductions",
        verbose_name=_("piège"),
    )
    explication = models.TextField(_("explication"), blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("traduction de piège")
        verbose_name_plural = _("traductions de pièges")
        constraints = [
            models.UniqueConstraint(
                fields=["piege", "langue"], name="piegetraduction_unique"
            )
        ]

    def __str__(self):
        return f"{self.piege} ({self.langue})"

    def prerequis_d_approbation(self):
        return (
            []
            if self.explication.strip()
            else [_("Écrivez l'explication dans cette langue.")]
        )


class ExempleTraduction(Traduction):
    exemple = models.ForeignKey(
        Exemple,
        on_delete=models.CASCADE,
        related_name="traductions",
        verbose_name=_("exemple"),
    )
    traduction = models.TextField(_("traduction"), blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("traduction d'exemple")
        verbose_name_plural = _("traductions d'exemples")
        constraints = [
            models.UniqueConstraint(
                fields=["exemple", "langue"], name="exempletraduction_unique"
            )
        ]

    def __str__(self):
        return f"{self.exemple} ({self.langue})"

    def prerequis_d_approbation(self):
        return (
            []
            if self.traduction.strip()
            else [_("Écrivez la phrase dans cette langue.")]
        )


# --- Contributeurs et relectures ----------------------------------------------


class Contributeur(TextesNormalises):
    """Profil public d'un compte : le nom crédité et les langues qu'il peut relire."""

    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contributeur",
        verbose_name=_("compte"),
    )
    nom_affiche = models.CharField(
        _("nom affiché"),
        max_length=150,
        help_text=_("Le nom crédité publiquement, dans n'importe quelle écriture."),
    )
    langues = ListeJSON(_("langues parlées"), vocabulaire="Langue", blank=True)
    licence_acceptee_le = models.DateTimeField(
        _("licence acceptée le"), null=True, blank=True
    )
    relit_langues = ListeJSON(
        _("langues relues"),
        vocabulaire="Langue",
        blank=True,
        help_text=_(
            "Le contenu que cette personne peut relire : « Français » pour les entrées, "
            "pièges et exemples, une autre langue pour leurs traductions."
        ),
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["nom_affiche"]
        verbose_name = _("contributeur")
        verbose_name_plural = _("contributeurs")

    def __str__(self):
        return self.nom_affiche


class Relecture(TextesNormalises):
    """Une relecture : quelqu'un approuve ou refuse un contenu. Elle ne se modifie plus."""

    type_contenu = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, verbose_name=_("type de contenu")
    )
    id_contenu = models.PositiveBigIntegerField(_("identifiant du contenu"))
    contenu = GenericForeignKey("type_contenu", "id_contenu")
    relecteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="relectures",
        verbose_name=_("relecteur"),
    )
    decision = models.CharField(
        _("décision"), max_length=10, choices=v.Decision.choices
    )
    commentaire = models.TextField(_("commentaire"), blank=True)
    date = models.DateTimeField(_("date"), default=timezone.now, editable=False)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-date"]
        verbose_name = _("relecture")
        verbose_name_plural = _("relectures")
        indexes = [models.Index(fields=["type_contenu", "id_contenu"])]

    def __str__(self):
        return f"{self.get_decision_display()} : {self.contenu}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(_("Une relecture ne se modifie pas."))
        with transaction.atomic():
            self.full_clean()
            super().save(*args, **kwargs)
            self.appliquer()

    def clean(self):
        contenu = self.contenu
        if not isinstance(contenu, Contenu):
            raise ValidationError(_("Ce contenu n'existe pas ou ne se relit pas."))
        if self.relecteur_id in contenu.editeurs():
            raise ValidationError(
                _(
                    "Vous ne pouvez pas relire un contenu que vous avez ajouté ou modifié."
                )
            )
        langue = contenu.langue_du_contenu()
        profil = Contributeur.objects.filter(utilisateur_id=self.relecteur_id).first()
        if profil is None or langue not in profil.relit_langues:
            raise ValidationError(
                _(
                    "Votre profil ne vous permet pas de relire le contenu en « %(langue)s ». "
                    "Les langues relues se règlent dans le profil de contributeur."
                )
                % {"langue": langue}
            )
        if contenu.statut == v.Statut.RETIRE:
            raise ValidationError(_("Un contenu retiré ne se relit plus."))
        if self.decision == v.Decision.APPROUVE:
            if contenu.statut == v.Statut.VALIDE:
                raise ValidationError(_("Ce contenu est déjà validé."))
            if self.relecteur_id in contenu.approbateurs():
                raise ValidationError(
                    _("Vous avez déjà approuvé cette version du contenu.")
                )
            manques = contenu.prerequis_d_approbation()
            if manques:
                raise ValidationError(manques)
        elif not self.commentaire.strip():
            raise ValidationError(
                {
                    "commentaire": _(
                        "Un refus s'accompagne d'un commentaire qui l'explique."
                    )
                }
            )

    def appliquer(self):
        """Met à jour le statut du contenu relu."""
        contenu = type(self.contenu).objects.get(pk=self.id_contenu)
        if self.decision == v.Decision.APPROUVE:
            approbations = len(contenu.approbateurs())
            contenu.statut = v.Statut.VALIDE if approbations >= 2 else v.Statut.RELU
        else:
            contenu.statut = v.Statut.REFUSE
        contenu._history_user = self.relecteur
        contenu.save(update_fields=["statut", "modifie_le"])

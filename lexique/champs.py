"""Champs de modèle propres au lexique."""

from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from lexique import vocabulaire


class ChampLignes(forms.CharField):
    """Champ de formulaire : une liste de textes, saisie à raison d'un texte par ligne."""

    widget = forms.Textarea(attrs={"rows": 4})

    def prepare_value(self, valeur):
        if isinstance(valeur, list):
            return "\n".join(valeur)
        return valeur

    def to_python(self, valeur):
        texte = super().to_python(valeur)
        return [ligne.strip() for ligne in texte.splitlines() if ligne.strip()]


class ListeJSON(models.JSONField):
    """Une liste stockée en JSON.

    Avec ``vocabulaire`` (le nom d'une classe de ``lexique.vocabulaire``), la
    liste contient des codes de ce vocabulaire, sans doublon ; sinon, des
    textes libres. Une liste vide signifie « aucun » (ou « partout » pour les
    régions) ; avec ``blank=False``, il faut au moins un élément.
    """

    def __init__(self, *args, vocabulaire=None, **kwargs):
        self.vocabulaire = vocabulaire
        kwargs.setdefault("default", list)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        nom, chemin, args, kwargs = super().deconstruct()
        if self.vocabulaire:
            kwargs["vocabulaire"] = self.vocabulaire
        return nom, chemin, args, kwargs

    def choix(self):
        return getattr(vocabulaire, self.vocabulaire).choices

    def validate(self, valeur, instance):
        super().validate(valeur, instance)
        if not isinstance(valeur, list) or not all(isinstance(e, str) for e in valeur):
            raise ValidationError(_("Une liste de textes est attendue."), code="liste")
        if not valeur and not self.blank:
            raise ValidationError(_("Choisissez au moins une valeur."), code="vide")
        if len(set(valeur)) != len(valeur):
            raise ValidationError(_("Une valeur apparaît deux fois."), code="doublon")
        if self.vocabulaire:
            connus = {code for code, _libelle in self.choix()}
            inconnus = [code for code in valeur if code not in connus]
            if inconnus:
                raise ValidationError(
                    _("Codes inconnus : %(codes)s."),
                    code="inconnu",
                    params={"codes": ", ".join(inconnus)},
                )

    def formfield(self, **kwargs):
        options = {
            "required": not self.blank,
            "label": capfirst(self.verbose_name),
            "help_text": self.help_text,
        }
        if self.vocabulaire:
            nombreux = len(self.choix()) > 12
            return forms.MultipleChoiceField(
                choices=self.choix(),
                widget=forms.SelectMultiple
                if nombreux
                else forms.CheckboxSelectMultiple,
                **options,
            )
        return ChampLignes(**options)

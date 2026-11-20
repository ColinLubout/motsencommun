"""Règles des mots de passe."""

from django.contrib.auth.password_validation import MinimumLengthValidator
from django.utils.translation import ngettext


class LongueurMinimale(MinimumLengthValidator):
    """Une longueur minimale, avec un conseil : une phrase de passe faite de mots ordinaires."""

    def get_help_text(self):
        return ngettext(
            "Au moins %(min_length)d caractère. Le plus simple : une phrase de passe de "
            "plusieurs mots ordinaires, comme « tortue lampe cerise voyage ».",
            "Au moins %(min_length)d caractères. Le plus simple : une phrase de passe de "
            "plusieurs mots ordinaires, comme « tortue lampe cerise voyage ».",
            self.min_length,
        ) % {"min_length": self.min_length}

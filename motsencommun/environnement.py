"""Lecture des réglages dans les variables d'environnement.

Sur le serveur, chaque réglage propre à l'installation vient d'une variable
d'environnement (voir ``deploiement/env.exemple``) et aucun n'a de valeur par
défaut : s'il en manque, le site refuse de démarrer et dit lesquels. En
développement local (``DJANGO_DEBUG=1``), des valeurs sans danger remplacent
les variables absentes.
"""

import os
import re
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

VALEURS_VRAIES = frozenset({"1", "true", "yes", "on", "oui", "vrai"})
VALEURS_FAUSSES = frozenset({"0", "false", "no", "off", "non", "faux"})

# Un chemin d'adresse : des parties faites de lettres ASCII, de chiffres, de « - »
# ou de « _ », séparées par « / ».
FORME_CHEMIN = re.compile(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*")


class Environnement:
    """Lit les variables d'environnement et note celles qui manquent.

    Une variable obligatoire absente ne déclenche pas d'erreur tout de suite :
    elle est notée, et ``verifier()`` signale ensuite toutes les absentes d'un
    coup. Une valeur présente mais invalide est refusée immédiatement.
    """

    def __init__(self, variables=None):
        self.variables = os.environ if variables is None else variables
        self.manquantes = []
        self.lues = set()
        self.developpement = self.booleen("DJANGO_DEBUG", defaut=False)

    def texte(self, nom):
        """Valeur de la variable sans espaces autour, ou None si elle est absente ou vide."""
        self.lues.add(nom)
        valeur = self.variables.get(nom, "").strip()
        return valeur or None

    def booleen(self, nom, *, defaut):
        """Interprète la variable comme oui ou non ; ``defaut`` si elle est absente."""
        valeur = self.texte(nom)
        if valeur is None:
            return defaut
        if valeur.lower() in VALEURS_VRAIES:
            return True
        if valeur.lower() in VALEURS_FAUSSES:
            return False
        raise ImproperlyConfigured(
            f"{nom} vaut « {valeur} », ce qui n'est ni oui ni non. "
            "Utilisez 1 ou 0 (ou true et false, oui et non)."
        )

    def obligatoire(self, nom, *, en_developpement):
        """Variable exigée sur le serveur.

        En développement, ``en_developpement`` la remplace si elle est absente.
        Sur le serveur, son absence est notée et la méthode renvoie None.
        """
        valeur = self.texte(nom)
        if valeur is not None:
            return valeur
        if self.developpement:
            return en_developpement
        self.manquantes.append(nom)
        return None

    def liste(self, nom, *, en_developpement):
        """Variable obligatoire contenant une liste d'éléments séparés par des virgules."""
        valeur = self.obligatoire(nom, en_developpement=",".join(en_developpement))
        if valeur is None:
            return []
        return [element.strip() for element in valeur.split(",") if element.strip()]

    def dossier(self, nom, *, en_developpement):
        """Variable obligatoire contenant le chemin absolu d'un dossier."""
        valeur = self.obligatoire(nom, en_developpement=str(en_developpement))
        if valeur is None:
            return None
        chemin = Path(valeur)
        if not chemin.is_absolute():
            raise ImproperlyConfigured(
                f"{nom} doit être un chemin absolu, comme /srv/motsencommun/donnees, "
                f"et non « {valeur} »."
            )
        return chemin

    def chemin_admin(self, nom):
        """Chemin de l'administration, ramené à la forme ``partie/`` (sans « / » au début).

        En développement, ``admin/`` sert par défaut. Sur le serveur, la valeur
        est obligatoire, et ``admin/``, trop facile à deviner, est refusé.
        """
        valeur = self.obligatoire(nom, en_developpement="admin/")
        if valeur is None:
            return None
        chemin = valeur.strip("/")
        if not FORME_CHEMIN.fullmatch(chemin):
            raise ImproperlyConfigured(
                f"{nom} vaut « {valeur} » : utilisez seulement des lettres sans accents, "
                "des chiffres, « - » et « _ », avec « / » entre les parties."
            )
        if chemin.lower() == "admin" and not self.developpement:
            raise ImproperlyConfigured(
                f"{nom} ne peut pas être « admin/ » sur le serveur : "
                "choisissez un chemin difficile à deviner."
            )
        return chemin + "/"

    def verifier(self):
        """Arrête tout s'il manque des variables obligatoires, en les nommant toutes."""
        if self.manquantes:
            raise ImproperlyConfigured(
                "Variables d'environnement manquantes : "
                f"{', '.join(self.manquantes)}. "
                "Elles sont décrites dans deploiement/env.exemple. "
                "Pour travailler en local, définissez DJANGO_DEBUG=1."
            )

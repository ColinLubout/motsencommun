"""Connexion à l'administration : double authentification et freinage des essais ratés.

Après 10 échecs en une heure, le compte visé ou l'adresse d'où viennent les
essais attend 15 minutes. Les compteurs vivent dans le cache partagé, sous une
empreinte (HMAC) du nom de compte ou de l'adresse : aucune adresse IP n'est
enregistrée.
"""

import hashlib
import hmac

from django import forms
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_otp import user_has_device
from django_otp.admin import OTPAdminAuthenticationForm
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

ECHECS_AVANT_BLOCAGE = 10
FENETRE_DES_ECHECS = 60 * 60  # une heure
DUREE_DU_BLOCAGE = 15 * 60  # quinze minutes


def adresse_du_client(request):
    """Adresse du visiteur. Derrière Caddy, c'est la dernière de X-Forwarded-For."""
    transmises = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if transmises:
        return transmises.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "")


def _cle(genre, valeur):
    empreinte = hmac.new(
        settings.SECRET_KEY.encode(), valeur.encode(), hashlib.sha256
    ).hexdigest()
    return f"connexion:{genre}:{empreinte}"


def _cibles(identifiant, adresse):
    """Ce qu'on compte : le compte visé (sans tenir compte des majuscules) et l'adresse."""
    if identifiant:
        yield "compte", identifiant.casefold()
    if adresse:
        yield "adresse", adresse


def est_bloque(identifiant, adresse):
    return any(
        cache.get(_cle(f"blocage-{g}", v)) for g, v in _cibles(identifiant, adresse)
    )


def noter_un_echec(identifiant, adresse):
    for genre, valeur in _cibles(identifiant, adresse):
        cle = _cle(f"echecs-{genre}", valeur)
        cache.add(cle, 0, FENETRE_DES_ECHECS)
        try:
            echecs = cache.incr(cle)
        except ValueError:  # le compteur vient d'expirer
            cache.set(cle, 1, FENETRE_DES_ECHECS)
            echecs = 1
        if echecs >= ECHECS_AVANT_BLOCAGE:
            cache.set(_cle(f"blocage-{genre}", valeur), True, DUREE_DU_BLOCAGE)


def oublier_les_echecs_du_compte(identifiant):
    if identifiant:
        cache.delete(_cle("echecs-compte", identifiant.casefold()))


def doit_donner_un_code(utilisateur):
    """Le superutilisateur donne toujours un code ; les autres, s'ils ont un appareil."""
    return utilisateur.is_superuser or user_has_device(utilisateur)


class FormulaireConnexion(OTPAdminAuthenticationForm):
    """Nom, mot de passe et, si nécessaire, code de double authentification."""

    otp_token = forms.CharField(
        required=False,
        label=_("Code de double authentification"),
        help_text=_(
            "Le code à six chiffres de votre application, ou un code de secours."
        ),
        widget=forms.TextInput(
            attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}
        ),
    )
    error_messages = {
        **AdminAuthenticationForm.error_messages,
        "trop_d_essais": _("Trop d'essais de connexion. Réessayez dans 15 minutes."),
    }
    otp_error_messages = {
        **OTPAdminAuthenticationForm.otp_error_messages,
        "token_required": _("Saisissez votre code de double authentification."),
        "invalid_token": _("Code invalide ou expiré. Réessayez avec un nouveau code."),
        "device_required": _(
            "Code invalide ou expiré. Réessayez avec un nouveau code."
        ),
        # Après un code faux, django-otp fait attendre quelques secondes, puis de plus en plus.
        "n_failed_attempts": _(
            "Vérification suspendue après %(failure_count)d essais ratés : "
            "réessayez dans un instant."
        ),
        "verification_not_allowed": _(
            "Vérification impossible pour le moment : réessayez dans un instant."
        ),
    }

    def _chosen_device(self, user):
        """L'appareil qui correspond au code saisi, sans liste à choisir.

        Un code à six chiffres vient de l'application ; un code de secours a huit
        lettres et chiffres. django-otp n'essaie pas tous les appareils l'un après
        l'autre (chaque échec freinerait les autres) : on choisit donc le bon ici.
        """
        code = (self.cleaned_data.get("otp_token") or "").strip()
        modele = TOTPDevice if code.isdigit() else StaticDevice
        return (
            modele.objects.select_for_update()
            .filter(user_id=user.pk, confirmed=True)
            .order_by("pk")
            .first()
        )

    def clean(self):
        identifiant = self.cleaned_data.get("username") or ""
        adresse = adresse_du_client(self.request) if self.request else ""
        if est_bloque(identifiant, adresse):
            raise ValidationError(
                self.error_messages["trop_d_essais"], code="trop_d_essais"
            )
        try:
            # Le mot de passe et le droit d'entrer, sans la double authentification
            # qu'OTPAdminAuthenticationForm imposerait à tout le monde.
            self.cleaned_data = AdminAuthenticationForm.clean(self)
            utilisateur = self.get_user()
            if utilisateur is not None and doit_donner_un_code(utilisateur):
                self.clean_otp(utilisateur)
        except ValidationError:
            noter_un_echec(identifiant, adresse)
            raise
        oublier_les_echecs_du_compte(identifiant)
        return self.cleaned_data

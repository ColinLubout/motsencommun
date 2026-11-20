"""Active la double authentification d'un compte : une application TOTP et des codes de secours.

Le compte superutilisateur ne peut pas ouvrir l'administration sans elle : c'est
donc cette commande, lancée sur le serveur, qui l'installe. Elle affiche une
seule fois le QR code à scanner et les codes de secours, dans le terminal de la
personne qui la lance ; rien n'est écrit dans un journal.
"""

import base64
import io

import qrcode
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_otp import devices_for_user
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

NOMBRE_DE_CODES_DE_SECOURS = 10


class Command(BaseCommand):
    help = (
        "Active la double authentification d'un compte : affiche une fois le QR code à "
        "scanner avec une application (Aegis, FreeOTP, Google Authenticator…), puis dix "
        "codes de secours à garder hors ligne."
    )

    def add_arguments(self, parser):
        parser.add_argument("nom_utilisateur", help="Le compte concerné.")
        parser.add_argument(
            "--remplacer",
            action="store_true",
            help="Remplace l'application et les codes de secours déjà enregistrés "
            "(téléphone perdu, codes épuisés).",
        )

    def lire_code(self):
        """Demande le code affiché par l'application (remplacé dans les tests)."""
        return input("Code à six chiffres affiché par l'application : ")

    def handle(self, *args, nom_utilisateur, remplacer, **options):
        utilisateur = get_user_model().objects.filter(username=nom_utilisateur).first()
        if utilisateur is None:
            raise CommandError(f"Aucun compte ne s'appelle « {nom_utilisateur} ».")
        if list(devices_for_user(utilisateur, confirmed=None)) and not remplacer:
            raise CommandError(
                "Ce compte a déjà la double authentification. Pour la refaire "
                "(téléphone perdu, codes épuisés), relancez avec --remplacer."
            )

        with transaction.atomic():
            if remplacer:
                TOTPDevice.objects.filter(user=utilisateur).delete()
                StaticDevice.objects.filter(user=utilisateur).delete()
            application = TOTPDevice.objects.create(
                user=utilisateur, name="Application", confirmed=False
            )
            self.afficher_le_qr_code(application)
            if not application.verify_token(self.lire_code().strip()):
                raise CommandError(
                    "Code incorrect : rien n'a été enregistré. Relancez la commande."
                )
            application.confirmed = True
            application.save()

            secours = StaticDevice.objects.create(
                user=utilisateur, name="Codes de secours"
            )
            codes = [
                StaticToken.random_token() for _ in range(NOMBRE_DE_CODES_DE_SECOURS)
            ]
            for code in codes:
                secours.token_set.create(token=code)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Double authentification activée."))
        self.stdout.write(
            "Codes de secours, à usage unique. Notez-les et gardez-les hors ligne, "
            "avec vos autres codes de récupération : ils ne s'afficheront plus."
        )
        for code in codes:
            self.stdout.write(f"    {code}")

    def afficher_le_qr_code(self, application):
        qr = qrcode.QRCode(border=2)
        qr.add_data(application.config_url)
        qr.make(fit=True)
        tampon = io.StringIO()
        qr.print_ascii(out=tampon, invert=True)
        cle = base64.b32encode(application.bin_key).decode()
        self.stdout.write(
            "Scannez ce QR code avec votre application de double authentification :"
        )
        self.stdout.write(tampon.getvalue())
        self.stdout.write(f"Ou saisissez cette clé à la main : {cle}")

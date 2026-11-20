"""La langue de l'interface vient de l'adresse : /fr/, /en/…

Jamais du navigateur ni d'un cookie : changer de langue, c'est suivre un lien
vers la même page sous un autre préfixe. Sans préfixe (l'administration, la
racine du site), c'est le français : l'administration reste en français
(décidé le 20 novembre 2026), et « / » mène à « /fr/ ».
"""

from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.utils import translation
from django.utils.cache import cc_delim_re

#: Ce dont la langue ne dépend jamais, ici : inutile de le déclarer dans « Vary ».
NE_DEPEND_PAS_DE = {"accept-language", "cookie"}


class LangueDeLAdresse(LocaleMiddleware):
    def process_request(self, request):
        langue = translation.get_language_from_path(request.path_info)
        translation.activate(langue or settings.LANGUAGE_CODE)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        reponse = super().process_response(request, response)
        if translation.get_language_from_path(request.path_info):
            return reponse
        # Sans préfixe, LocaleMiddleware ajoute « Vary: Accept-Language » (et
        # « Cookie » à sa redirection vers /fr/) : ici, la langue n'en dépend pas.
        a_retirer = NE_DEPEND_PAS_DE if reponse is not response else {"accept-language"}
        if reponse.has_header("Vary"):
            restants = [
                entete
                for entete in cc_delim_re.split(reponse["Vary"])
                if entete.strip().lower() not in a_retirer
            ]
            if restants:
                reponse["Vary"] = ", ".join(restants)
            else:
                del reponse["Vary"]
        return reponse

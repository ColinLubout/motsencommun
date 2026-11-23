"""En-têtes de sécurité des pages que Django rend.

Le ``SecurityMiddleware`` de Django pose déjà HSTS, ``Referrer-Policy`` et
``X-Content-Type-Options`` (voir les réglages ``SECURE_*``), et
``XFrameOptionsMiddleware`` interdit l'affichage dans un cadre. Ce module ajoute
ce que Django 5.2 ne sait pas poser :

- la politique de sécurité du contenu (CSP) : tout vient de ce site, et aucun
  autre site ne peut afficher nos pages dans un cadre ;
- ``Permissions-Policy`` : ni caméra, ni micro, ni position.

Les pages à intégrer (``/integrer/``) sont la seule exception au cadre : leur
vue porte ``@xframe_options_exempt``, et ce module leur laisse alors tout site
pour parent. Caddy ajoute les mêmes en-têtes aux fichiers qu'il sert lui-même.
"""

#: Tout vient de ce site : scripts, styles, polices, images, et nulle part
#: ailleurs. Une balise <base> ne peut pas détourner les liens, et les formulaires
#: ne s'envoient qu'ici.
POLITIQUE_COMMUNE = "default-src 'self'; base-uri 'none'; form-action 'self'"

#: Aucun autre site ne peut afficher la page dans un cadre.
POLITIQUE = f"{POLITIQUE_COMMUNE}; frame-ancestors 'none'"

#: Les pages à intégrer : n'importe quel site peut les afficher dans un cadre.
POLITIQUE_INTEGRABLE = f"{POLITIQUE_COMMUNE}; frame-ancestors *"

#: Caméra, micro et position coupés (jusqu'aux enregistrements de la phase 4).
PERMISSIONS = "camera=(), microphone=(), geolocation=()"


class EntetesDeSecurite:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reponse = self.get_response(request)
        integrable = getattr(reponse, "xframe_options_exempt", False)
        reponse.headers.setdefault(
            "Content-Security-Policy",
            POLITIQUE_INTEGRABLE if integrable else POLITIQUE,
        )
        reponse.headers.setdefault("Permissions-Policy", PERMISSIONS)
        return reponse

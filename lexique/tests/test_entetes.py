"""En-têtes de sécurité : CSP, cadres, HSTS, Referrer-Policy et Permissions-Policy."""

import pytest
from django.conf import settings

from motsencommun.entetes import PERMISSIONS, POLITIQUE, POLITIQUE_INTEGRABLE

#: Les pages ordinaires : aucun autre site ne peut les afficher dans un cadre.
PAGES_ORDINAIRES = [
    "/fr/",
    "/en/",
    "/fr/expressions/",
    "/fr/niveau/b1/",
    "/fr/expressions/poser-un-lapin/",
    "/fr/recherche/?q=lapin",
    "/fr/telecharger/",
    "/fr/a-propos/",
    "/fr/page-qui-n-existe-pas/",
    "/fr/expressions/expression-secrete/",
    "/fr/expressions/expression-secrete/integrer/",  # une 404, pas une page à intégrer
    f"/{settings.CHEMIN_ADMIN}login/",
]

PAGES_A_INTEGRER = [
    "/fr/expressions/poser-un-lapin/integrer/",
    "/en/expressions/poser-un-lapin/integrer/",
    "/fr/expressions/poser-un-lapin/integrer/?mon_niveau=A2",
]


def directives(politique):
    """{"default-src": "'self'", …} : la politique découpée en directives."""
    return dict(directive.strip().split(" ", 1) for directive in politique.split(";"))


def test_la_politique_de_securite_du_contenu_est_celle_du_prd():
    """Critère du PRD : CSP « default-src 'self' » et « frame-ancestors 'none' »."""
    assert directives(POLITIQUE) == {
        "default-src": "'self'",
        "base-uri": "'none'",
        "form-action": "'self'",
        "frame-ancestors": "'none'",
    }
    assert directives(POLITIQUE_INTEGRABLE) == {
        **directives(POLITIQUE),
        "frame-ancestors": "*",
    }


@pytest.mark.parametrize("adresse", PAGES_ORDINAIRES)
def test_chaque_page_porte_les_en_tetes_de_securite(client, site_public, adresse):
    """Critère du PRD : CSP, Referrer-Policy et Permissions-Policy partout."""
    reponse = client.get(adresse)
    assert reponse["Content-Security-Policy"] == POLITIQUE
    assert reponse["X-Frame-Options"] == "DENY"
    assert reponse["Referrer-Policy"] == "no-referrer"
    assert reponse["X-Content-Type-Options"] == "nosniff"
    assert reponse["Permissions-Policy"] == PERMISSIONS
    for fonction in ("camera", "microphone", "geolocation"):
        assert f"{fonction}=()" in reponse["Permissions-Policy"]


@pytest.mark.parametrize("adresse", PAGES_A_INTEGRER)
def test_seules_les_pages_a_integrer_acceptent_un_cadre(client, site_public, adresse):
    """Critère du PRD : les pages /integrer/ sont les seules qu'un autre site peut encadrer."""
    reponse = client.get(adresse)
    assert reponse.status_code == 200
    assert reponse["Content-Security-Policy"] == POLITIQUE_INTEGRABLE
    assert "X-Frame-Options" not in reponse
    # Le reste ne change pas.
    assert reponse["Referrer-Policy"] == "no-referrer"
    assert reponse["Permissions-Policy"] == PERMISSIONS


def test_hsts_pour_un_an_en_https(client, site_public):
    """Critère du PRD : HSTS d'un an, sans liste de préchargement."""
    reponse = client.get("/fr/", secure=True)
    assert reponse["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert "preload" not in reponse["Strict-Transport-Security"]


def test_derriere_caddy_django_sait_que_la_page_est_en_https(client, site_public):
    """Caddy reçoit le visiteur en HTTPS et transmet « X-Forwarded-Proto: https »."""
    assert "Strict-Transport-Security" in client.get(
        "/fr/", headers={"x-forwarded-proto": "https"}
    )
    # En HTTP, HSTS n'aurait pas de sens (et le navigateur l'ignorerait).
    assert "Strict-Transport-Security" not in client.get("/fr/")

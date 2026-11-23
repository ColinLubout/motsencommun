"""Vie privée des pages publiques : ni cookie, ni autre site, ni JavaScript nécessaire."""

import re
from pathlib import Path

import pytest
from django.conf import settings

ADRESSES_PUBLIQUES = [
    "/fr/",
    "/en/",
    "/fr/expressions/",
    "/fr/expressions/?niveau=B1&type=sens_figure&theme=relations&registre=familier",
    "/fr/niveau/b1/",
    "/fr/type/sens-figure/",
    "/fr/theme/relations/",
    "/fr/expressions/poser-un-lapin/",
    "/fr/expressions/poser-un-lapin/?mon_niveau=A2",
    "/en/expressions/poser-un-lapin/",
    "/fr/expressions/poser-un-lapin/integrer/",
    "/fr/recherche/?q=lapin",
    "/fr/telecharger/",
    "/fr/a-propos/",
    "/fr/expressions/expression-secrete/",
    "/fr/page-qui-n-existe-pas/",
]

#: Attributs par lesquels une page fait charger quelque chose au navigateur.
RESSOURCES = re.compile(
    r"""<(?:script|img|iframe|frame|embed|object|source|audio|video|track|input)\b[^>]*"""
    r"""\s(?:src|srcset|data|poster)=["']([^"']*)["']"""
    r"""|<link\b[^>]*\shref=["']([^"']*)["']"""
    r"""|url\(\s*["']?([^"')]+)""",
    re.IGNORECASE,
)


def reponses(client):
    for adresse in ADRESSES_PUBLIQUES:
        yield adresse, client.get(adresse)


def test_aucune_page_publique_ne_pose_de_cookie(client, site_public):
    """Critère du PRD : aucune réponse publique ne contient « Set-Cookie »."""
    for adresse, reponse in reponses(client):
        assert not reponse.cookies, adresse
        assert "Set-Cookie" not in reponse.headers, adresse
        assert "Cookie" not in reponse.get("Vary", ""), (
            f"{adresse} : la page ne dépend pas des cookies du visiteur"
        )


def test_aucune_page_publique_ne_fait_appel_a_un_autre_site(client, site_public):
    """Critère du PRD : aucune page ne charge quoi que ce soit d'un autre domaine.

    Les liens <a> vers d'autres sites (la licence, le code) ne chargent rien :
    le navigateur ne les suit que si on clique.
    """
    for adresse, reponse in reponses(client):
        for groupes in RESSOURCES.findall(reponse.content.decode()):
            ressource = next(g for g in groupes if g)
            assert not re.match(
                r"^(?:[a-z][a-z0-9+.-]*:)?//", ressource, re.IGNORECASE
            ), f"{adresse} charge {ressource}"


def test_la_feuille_de_style_ne_fait_appel_a_aucun_autre_site():
    for feuille in Path(settings.BASE_DIR, "static").rglob("*.css"):
        texte = feuille.read_text("utf-8")
        assert "@import" not in texte
        assert not re.search(r"url\(\s*[\"']?(?:[a-z]+:)?//", texte, re.IGNORECASE), (
            feuille
        )


def test_le_seul_javascript_est_le_fichier_du_site(client, site_public):
    """Aucun script écrit dans le HTML ni attribut on… : seulement le fichier du site.

    La page à intégrer n'a pas de script du tout. Que chaque page marche sans
    JavaScript est vérifié dans un vrai navigateur (test_navigateur.py).
    """
    for adresse, reponse in reponses(client):
        contenu = reponse.content.decode()
        scripts = re.findall(r"<script\b([^>]*)>(.*?)</script>", contenu, re.DOTALL)
        attendus = (
            []
            if "/integrer/" in adresse
            else [(' src="/static/mots-en-commun.js"', "")]
        )
        assert scripts == attendus, adresse
        assert not re.search(r"<[^>]+\son[a-z]+=", contenu, re.IGNORECASE), adresse


def test_aucune_page_publique_n_a_de_formulaire_protege_par_csrf(client, site_public):
    for adresse, reponse in reponses(client):
        contenu = reponse.content.decode()
        assert "csrfmiddlewaretoken" not in contenu, adresse
        assert 'method="post"' not in contenu.lower(), adresse


@pytest.mark.parametrize(
    "adresse", ["/fr/expressions/", "/fr/expressions/poser-un-lapin/"]
)
def test_l_impression_cache_la_navigation_et_les_formulaires(
    client, site_public, adresse
):
    """Critère du PRD : les listes s'impriment proprement depuis le navigateur."""
    feuille = Path(settings.BASE_DIR, "static", "mots-en-commun.css").read_text("utf-8")
    impression = feuille[feuille.index("@media print") :]
    contenu = client.get(adresse).content.decode()
    assert '<link rel="stylesheet" href="/static/mots-en-commun.css">' in contenu
    for classe in ("recherche", "mon-niveau", "navigation", "langues"):
        assert f'class="{classe}"' in contenu
        assert f".{classe}" in impression
    assert ".filtres" in impression and ".pagination" in impression
    assert "break-inside: avoid" in impression

"""Le site dans un vrai navigateur (Chromium, par Playwright) : confort de lecture,
Mon niveau, pages sans JavaScript, accessibilité (axe), espacements, téléphone.

Lancer seulement ces tests : ``uv run pytest -m navigateur`` ; tous les autres :
``uv run pytest -m "not navigateur"``. Il faut Chromium : ``uv run playwright
install --with-deps chromium``.
"""

import os

import pytest
from axe_playwright_python.sync_playwright import Axe
from django.conf import settings
from playwright.sync_api import sync_playwright

from lexique.tests.conftest import creer_entree, rendre_public

pytestmark = pytest.mark.navigateur

CONFORT = "mots-en-commun.confort-de-lecture"
MON_NIVEAU = "mots-en-commun.mon-niveau"
FICHE = "/fr/expressions/poser-un-lapin/"

#: Les impacts qu'axe juge sérieux : aucun n'est accepté.
IMPACTS_SERIEUX = {"serious", "critical"}


@pytest.fixture(scope="session")
def chromium():
    # Playwright fait tourner une boucle asyncio dans ce fil : Django doit
    # accepter d'y servir la base de données de test.
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
    with sync_playwright() as playwright:
        # Un test simule un autre site par une page que Playwright fournit lui-même :
        # Chromium, qui ne sait pas d'où elle vient, lui interdirait sinon d'afficher
        # notre serveur de test local dans un cadre (Local Network Access).
        navigateur = playwright.chromium.launch(
            args=["--disable-features=LocalNetworkAccessChecks"]
        )
        yield navigateur
        navigateur.close()


class Visite:
    """Une page ouverte dans un contexte de navigation neuf, avec ses requêtes."""

    def __init__(self, chromium, live_server, **options):
        self.racine = live_server.url
        self.contexte = chromium.new_context(**options)
        self.page = self.contexte.new_page()
        self.requetes = []
        self.erreurs = []
        self.page.on("request", lambda requete: self.requetes.append(requete.url))
        self.page.on(
            "console",
            lambda message: (
                self.erreurs.append(message.text) if message.type == "error" else None
            ),
        )

    def refus_de_la_politique(self):
        """Ce que la politique de sécurité du contenu (CSP) a bloqué jusqu'ici."""
        return [
            erreur for erreur in self.erreurs if "Content Security Policy" in erreur
        ]

    def aller(self, chemin):
        self.page.goto(self.racine + chemin)
        self.page.wait_for_load_state("networkidle")
        self.page.evaluate("document.fonts.ready.then(() => true)")
        return self.page

    def style(self, propriete, selecteur="body"):
        return self.page.evaluate(
            f"getComputedStyle(document.querySelector({selecteur!r}))[{propriete!r}]"
        )

    def stockage(self, cle):
        return self.page.evaluate(f"localStorage.getItem({cle!r})")

    def polices_demandees(self, nom):
        return [adresse for adresse in self.requetes if nom in adresse]

    def fermer(self):
        self.contexte.close()


@pytest.fixture
def visite(chromium, live_server):
    visites = []

    def ouvrir(**options):
        nouvelle = Visite(chromium, live_server, **options)
        visites.append(nouvelle)
        return nouvelle

    yield ouvrir
    for ouverte in visites:
        ouverte.fermer()


# --- Confort de lecture -------------------------------------------------------


def test_le_confort_de_lecture(visite, site_public):
    """Critère du PRD : OpenDyslexic, texte plus grand et plus espacé, police chargée
    seulement une fois le bouton activé, choix retenu sans cookie."""
    v = visite()
    page = v.aller(FICHE)
    bouton = page.locator("#bouton-confort")
    assert bouton.is_visible()
    assert bouton.get_attribute("aria-pressed") == "false"
    assert v.polices_demandees("OpenDyslexic") == [], (
        "personne d'autre ne la télécharge"
    )
    taille_avant = float(v.style("fontSize").removesuffix("px"))

    bouton.click()
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready.then(() => true)")

    assert v.polices_demandees("OpenDyslexic"), "téléchargée une fois le bouton activé"
    assert "OpenDyslexic" in v.style("fontFamily")
    assert page.evaluate("document.fonts.check('16px OpenDyslexic')")
    assert float(v.style("fontSize").removesuffix("px")) > taille_avant
    assert float(v.style("letterSpacing").removesuffix("px")) > 0
    assert float(v.style("wordSpacing").removesuffix("px")) > 0
    assert bouton.get_attribute("aria-pressed") == "true"
    assert v.stockage(CONFORT) == "oui"

    page.reload()
    assert page.evaluate("document.documentElement.classList.contains('confort')")
    assert page.locator("#bouton-confort").get_attribute("aria-pressed") == "true"

    # Plus d'italique : la traduction, en italique d'ordinaire, s'affiche droite.
    page = v.aller("/en/expressions/poser-un-lapin/")
    assert v.style("fontStyle", ".traduction") == "normal"

    page.locator("#bouton-confort").click()
    assert v.stockage(CONFORT) is None
    assert v.contexte.cookies() == [], (
        "ni cookie pour le confort, ni pour quoi que ce soit"
    )


def test_le_fond_creme_du_confort_de_lecture(visite, site_public):
    for theme in ("light", "dark"):
        v = visite(color_scheme=theme)
        page = v.aller(FICHE)
        fond_avant = v.style("backgroundColor", "html")
        page.locator("#bouton-confort").click()
        assert v.style("backgroundColor", "html") != fond_avant, theme


# --- Sans JavaScript ----------------------------------------------------------


def test_sans_javascript_tout_marche_et_le_bouton_est_cache(visite, site_public):
    """Critère du PRD : le bouton est caché sans JavaScript ; chaque page marche sans."""
    v = visite(java_script_enabled=False)
    page = v.aller("/fr/expressions/")
    assert page.locator("#bouton-confort").is_hidden()
    assert page.locator("h1").inner_text() == "Toutes les expressions"

    page.select_option("#choix-niveau", "A2")
    page.locator("form.mon-niveau button").click()
    page.wait_for_load_state()
    assert "mon_niveau=A2" in page.url

    page.locator(".vedette a", has_text="poser un lapin").click()
    page.wait_for_load_state()
    assert "mon_niveau=A2" in page.url
    assert "Pas de version de niveau A2 : voici la version B1." in page.content()
    assert v.polices_demandees("OpenDyslexic") == []


# --- Mon niveau ---------------------------------------------------------------


def test_mon_niveau_est_retenu_dans_le_navigateur(visite, site_public):
    v = visite()
    page = v.aller("/fr/expressions/")
    page.select_option("#choix-niveau", "B2")
    page.locator("form.mon-niveau button").click()
    page.wait_for_load_state()
    assert v.stockage(MON_NIVEAU) == "B2"

    page = v.aller(FICHE)
    assert page.url.endswith("?mon_niveau=B2"), (
        "une page ouverte sans niveau reprend le sien"
    )
    assert "Pas de version de niveau B2 : voici la version B1." in page.content()

    page.select_option("#choix-niveau", "")
    page.locator("form.mon-niveau button").click()
    page.wait_for_load_state()
    assert v.stockage(MON_NIVEAU) is None
    page = v.aller(FICHE)
    assert page.url.endswith(FICHE)
    assert v.contexte.cookies() == []


def test_un_lien_partage_ne_change_pas_le_niveau_retenu(visite, site_public):
    v = visite()
    page = v.aller("/fr/expressions/")
    page.select_option("#choix-niveau", "A2")
    page.locator("form.mon-niveau button").click()
    page.wait_for_load_state()
    v.aller(f"{FICHE}?mon_niveau=C1")
    assert v.stockage(MON_NIVEAU) == "A2"


# --- Accessibilité ------------------------------------------------------------

PAGES = [
    "/fr/",
    "/fr/expressions/",
    "/fr/theme/relations/",
    FICHE,
    "/en/expressions/poser-un-lapin/",
    FICHE + "integrer/",
    "/fr/recherche/?q=lapin",
    "/fr/telecharger/",
    "/fr/a-propos/",
    "/fr/page-introuvable/",
]


def problemes_serieux(page):
    resultats = Axe().run(page)
    return [
        f"{violation['id']} ({violation['impact']}) : {violation['help']} → "
        + "; ".join(noeud["html"][:120] for noeud in violation["nodes"][:3])
        for violation in resultats.response["violations"]
        if violation["impact"] in IMPACTS_SERIEUX
    ]


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_axe_ne_trouve_aucun_probleme_serieux(visite, site_public, theme):
    """Critère du PRD : un contrôle automatique d'accessibilité (axe), sans problème sérieux."""
    v = visite(color_scheme=theme)
    for chemin in PAGES:
        v.aller(chemin)
        assert problemes_serieux(v.page) == [], f"{chemin} ({theme})"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_axe_avec_le_confort_de_lecture(visite, site_public, theme):
    v = visite(color_scheme=theme)
    v.contexte.add_init_script(f"localStorage.setItem({CONFORT!r}, 'oui')")
    for chemin in ("/fr/expressions/", FICHE):
        v.aller(chemin)
        assert v.page.evaluate("document.documentElement.classList.contains('confort')")
        assert problemes_serieux(v.page) == [], f"{chemin} (confort, {theme})"


# --- Mise en page -------------------------------------------------------------

#: Espacements de texte du critère WCAG 2.2 1.4.12, comme une extension les appliquerait.
ESPACEMENTS_WCAG = """
* { line-height: 1.5 !important; letter-spacing: 0.12em !important;
    word-spacing: 0.16em !important; }
p { margin-block-end: 2em !important; }
"""


def deborde(page):
    """Les éléments qui dépassent à droite de l'écran (liste vide : rien ne déborde)."""
    return page.evaluate(
        """() => {
          const largeur = document.documentElement.clientWidth;
          if (document.documentElement.scrollWidth <= largeur) return [];
          return [...document.querySelectorAll("body *")]
            .filter(e => e.getBoundingClientRect().right > largeur + 1)
            .map(e => `${e.tagName.toLowerCase()}.${e.className} → ${Math.round(e.getBoundingClientRect().right)} px`)
            .slice(0, 8);
        }"""
    )


@pytest.mark.parametrize("largeur", [320, 768, 1280])
def test_rien_ne_deborde_quelle_que_soit_la_largeur(visite, site_public, largeur):
    v = visite(viewport={"width": largeur, "height": 800})
    for chemin in ("/fr/", "/fr/expressions/", FICHE):
        v.aller(chemin)
        assert deborde(v.page) == [], f"{chemin} à {largeur} px"


@pytest.mark.parametrize("confort", [False, True])
def test_les_espacements_du_lecteur_ne_cassent_pas_la_page(
    visite, site_public, confort
):
    """WCAG 2.2, critère 1.4.12 : les espacements imposés par le lecteur ne cassent rien.

    Une extension du navigateur n'est pas tenue par notre politique de sécurité du
    contenu : le style ajouté ici non plus (``bypass_csp``).
    """
    v = visite(viewport={"width": 360, "height": 800}, bypass_csp=True)
    if confort:
        v.contexte.add_init_script(f"localStorage.setItem({CONFORT!r}, 'oui')")
    for chemin in ("/fr/expressions/", FICHE):
        page = v.aller(chemin)
        page.add_style_tag(content=ESPACEMENTS_WCAG)
        assert deborde(page) == [], chemin
        assert page.locator("#champ-recherche").is_visible()
        assert page.locator("h1").is_visible()


def test_le_mode_sombre_suit_l_appareil(visite, site_public):
    clair = visite(color_scheme="light")
    clair.aller(FICHE)
    sombre = visite(color_scheme="dark")
    sombre.aller(FICHE)
    assert clair.style("backgroundColor", "html") == "rgb(251, 250, 247)"
    assert sombre.style("backgroundColor", "html") == "rgb(22, 24, 29)"


def test_literata_et_seulement_le_fichier_utile(visite, site_public, proprietaire):
    """Le fichier cyrillique ne se télécharge que pour une page qui en contient."""
    v = visite()
    v.aller(FICHE)
    assert v.polices_demandees("literata-latin")
    assert v.polices_demandees("literata-cyrillique") == []
    assert "Literata" in v.style("fontFamily")

    rendre_public(creer_entree(proprietaire, slug="kyiv", vedette="aller à Київ"))
    v.aller("/fr/expressions/kyiv/")
    assert v.polices_demandees("literata-cyrillique")


# --- Sécurité du contenu (CSP) et cadres ----------------------------------------


def test_la_politique_de_securite_ne_bloque_rien_sur_le_site(visite, site_public):
    """Tout vient du site et rien n'est écrit dans le HTML : la CSP ne refuse rien."""
    v = visite()
    v.contexte.add_init_script(f"localStorage.setItem({CONFORT!r}, 'oui')")
    for chemin in PAGES:
        v.aller(chemin)
    assert v.polices_demandees("OpenDyslexic"), "le confort de lecture a bien servi"
    assert v.refus_de_la_politique() == []


def ouvrir_l_administration(visite, client_proprietaire):
    """Un navigateur connecté en propriétaire (double authentification passée)."""
    v = visite()
    v.contexte.add_cookies(
        [
            {
                "name": settings.SESSION_COOKIE_NAME,
                "value": client_proprietaire.cookies[
                    settings.SESSION_COOKIE_NAME
                ].value,
                "url": v.racine,
            }
        ]
    )
    return v


def test_la_politique_de_securite_ne_bloque_rien_dans_l_administration(
    visite, site_public, client_proprietaire, proprietaire
):
    admin = f"/{settings.CHEMIN_ADMIN}"
    entree = site_public.lapin.pk
    contributeur = proprietaire.contributeur.pk
    v = ouvrir_l_administration(visite, client_proprietaire)
    for chemin in (
        admin,
        f"{admin}lexique/entree/",
        f"{admin}lexique/entree/add/",
        f"{admin}lexique/entree/{entree}/change/",
        f"{admin}lexique/exemple/{site_public.exemple.pk}/change/",
        f"{admin}lexique/contributeur/{contributeur}/change/",
        f"{admin}lexique/relecture/add/",
    ):
        page = v.aller(chemin)
        assert page.locator("#site-name").is_visible(), chemin
    assert v.refus_de_la_politique() == []

    deconnecte = visite()
    deconnecte.aller(f"{admin}login/")
    assert deconnecte.refus_de_la_politique() == []


def test_seules_les_pages_a_integrer_s_affichent_dans_un_autre_site(
    visite, site_public
):
    """Critère du PRD : les pages /integrer/ sont les seules qu'un autre site peut encadrer."""
    v = visite()

    def lecon(chemin):
        """Ouvre une page d'un autre site qui encadre ``chemin`` de notre site.

        127.0.0.1 est une autre origine que localhost, celle du site. Un seul cadre
        par page : le serveur de test répond mal à deux pages à la fois (une seule
        connexion SQLite en mémoire).
        """
        cours = v.racine.replace("localhost", "127.0.0.1") + f"/autre-site{chemin}"
        assert cours.startswith("http://127.0.0.1:")
        html = f'<!doctype html><title>Leçon</title><iframe src="{v.racine}{chemin}"></iframe>'
        v.contexte.route(
            cours,
            lambda route: route.fulfill(
                body=html, content_type="text/html; charset=utf-8"
            ),
        )
        v.page.goto(cours)
        v.page.wait_for_load_state("networkidle")
        return v.page.frame_locator("iframe")

    # La fiche ordinaire : le navigateur la refuse, à cause de notre politique.
    lecon(FICHE)
    cadre = v.page.locator("iframe").element_handle().content_frame()
    assert "poser un lapin" not in cadre.content()
    assert any("frame-ancestors 'none'" in refus for refus in v.refus_de_la_politique())

    # La page à intégrer s'affiche.
    integree = lecon(FICHE + "integrer/")
    assert integree.locator("h1").inner_text() == "poser un lapin à qqn"

    # Le lien vers la fiche complète s'ouvre dans un nouvel onglet, hors du cadre.
    with v.page.expect_popup() as onglet:
        integree.get_by_role("link", name="Voir cette fiche sur Mots en commun").click()
    onglet.value.wait_for_url(v.racine + FICHE)
    assert onglet.value.locator("h1").inner_text() == "poser un lapin à qqn"

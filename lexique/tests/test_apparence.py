"""Apparence : contrastes, polices, script, poids des pages (sans navigateur)."""

import re
from pathlib import Path

import pytest
from django.conf import settings

STATIQUES = Path(settings.BASE_DIR, "static")
FEUILLE = (STATIQUES / "mots-en-commun.css").read_text("utf-8")
SCRIPT = (STATIQUES / "mots-en-commun.js").read_text("utf-8")


# --- Couleurs et contrastes ---------------------------------------------------


def bloc(debut):
    """Le contenu du bloc CSS qui suit ``debut`` (jusqu'à l'accolade fermante)."""
    position = FEUILLE.index(debut) + len(debut)
    return FEUILLE[position : FEUILLE.index("}", position)]


def couleurs(texte):
    return dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})\s*;", texte))


CLAIR = couleurs(bloc("\n:root {"))
SOMBRE = {**CLAIR, **couleurs(bloc("@media (prefers-color-scheme: dark) {\n  :root {"))}
THEMES = {
    "clair": CLAIR,
    "sombre": SOMBRE,
    "confort clair": {**CLAIR, **couleurs(bloc("\n:root.confort {"))},
    "confort sombre": {
        **SOMBRE,
        **couleurs(bloc("@media (prefers-color-scheme: dark) {\n  :root.confort {")),
    },
}

#: (couleur du texte, couleur du fond) de tout ce qui s'écrit sur la page.
PAIRES = [
    ("--texte", "--fond"),
    ("--texte", "--fond-encart"),
    ("--texte-discret", "--fond"),
    ("--texte-discret", "--fond-encart"),
    ("--accent", "--fond"),
    ("--accent", "--fond-encart"),
    ("--accent", "--accent-fond"),
    ("--fond", "--accent"),  # boutons
    ("--texte", "--surlignage"),
    ("--alerte", "--alerte-fond"),
    ("--gravite-faible", "--fond-encart"),
    ("--gravite-moyenne", "--fond-encart"),
    ("--gravite-elevee", "--fond-encart"),
    ("--gravite-faible", "--fond"),
    ("--gravite-elevee", "--fond"),
]


def luminance(couleur):
    """Luminance relative d'une couleur #rrggbb (WCAG 2.2)."""
    composantes = [int(couleur[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineaires = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in composantes
    ]
    return 0.2126 * lineaires[0] + 0.7152 * lineaires[1] + 0.0722 * lineaires[2]


def contraste(premier_plan, arriere_plan):
    clair, sombre = sorted(
        (luminance(premier_plan), luminance(arriere_plan)), reverse=True
    )
    return (clair + 0.05) / (sombre + 0.05)


def test_les_quatre_themes_definissent_les_memes_couleurs():
    assert all(set(theme) == set(CLAIR) for theme in THEMES.values())
    assert len(CLAIR) >= 13


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize(("texte", "fond"), PAIRES)
def test_chaque_texte_a_un_contraste_d_au_moins_4_5(theme, texte, fond):
    """WCAG 2.2 AA, dans les deux modes et avec le confort de lecture."""
    couleurs_du_theme = THEMES[theme]
    rapport = contraste(couleurs_du_theme[texte], couleurs_du_theme[fond])
    assert rapport >= 4.5, f"{theme} : {texte} sur {fond} = {rapport:.2f}"


def test_le_mode_sombre_suit_l_appareil_sans_bouton():
    assert "@media (prefers-color-scheme: dark)" in FEUILLE
    assert "color-scheme: light dark" in FEUILLE


def test_le_fond_du_confort_de_lecture_est_creme():
    for theme in ("confort clair", "confort sombre"):
        rouge, vert, bleu = (
            int(THEMES[theme]["--fond"][i : i + 2], 16) for i in (1, 3, 5)
        )
        assert rouge > vert > bleu, f"{theme} : un fond chaud, crème"


# --- Polices ------------------------------------------------------------------


def faces():
    return re.findall(r"@font-face \{(.*?)\}", FEUILLE, re.DOTALL)


def test_les_polices_sont_sur_le_site_avec_leur_licence():
    for face in faces():
        for adresse in re.findall(r'url\("([^"]+)"\)', face):
            assert not re.match(r"^([a-z]+:)?//", adresse), adresse
            assert (STATIQUES / adresse).is_file(), adresse
        assert "font-display: swap;" in face
    assert (STATIQUES / "polices" / "OFL-Literata.txt").is_file()
    assert (STATIQUES / "polices" / "OFL-OpenDyslexic.txt").is_file()
    for licence in (STATIQUES / "polices").glob("OFL-*.txt"):
        assert "SIL Open Font License" in licence.read_text("utf-8")


def test_literata_est_decoupee_par_ecriture():
    """Le navigateur ne télécharge le fichier cyrillique que pour une page qui en a besoin."""
    literata = [face for face in faces() if '"Literata"' in face]
    assert len(literata) == 2
    assert all("unicode-range:" in face for face in literata)
    assert all("font-weight: 400 700;" in face for face in literata)


def test_opendyslexic_ne_sert_qu_au_confort_de_lecture():
    """Une police qu'aucune règle n'utilise n'est jamais téléchargée."""
    sans_commentaires = re.sub(r"/\*.*?\*/", "", FEUILLE, flags=re.DOTALL)
    sans_les_faces = re.sub(
        r"@font-face \{.*?\}", "", sans_commentaires, flags=re.DOTALL
    )
    regles = re.findall(r"([^{}]+)\{[^{}]*OpenDyslexic[^{}]*\}", sans_les_faces)
    assert [selecteur.strip() for selecteur in regles] == [":root.confort"]


def test_le_confort_de_lecture_agrandit_et_espace_le_texte():
    assert "font-size: 125%;" in bloc("\n:root.confort {")
    confort = bloc(".confort body {")
    assert "letter-spacing" in confort and "word-spacing" in confort
    assert "line-height: 1.8" in confort
    assert "font-style: normal" in bloc(".confort .traduction {")


# --- Script -------------------------------------------------------------------


def test_le_script_ne_suit_personne():
    """JavaScript pour le confort du lecteur seulement : rien ne part du navigateur."""
    for interdit in (
        "document.cookie",
        "fetch(",
        "XMLHttpRequest",
        "sendBeacon",
        "WebSocket",
        "navigator.",
        "eval(",
    ):
        assert interdit not in SCRIPT, interdit
    assert "localStorage" in SCRIPT


def test_les_pages_n_ont_que_le_script_du_site(client, site_public):
    page = client.get("/fr/expressions/poser-un-lapin/").content.decode()
    scripts = re.findall(r"<script\b([^>]*)>(.*?)</script>", page, re.DOTALL)
    assert scripts == [(' src="/static/mots-en-commun.js"', "")]
    assert (
        '<button type="button" id="bouton-confort" class="bouton-confort"'
        ' aria-pressed="false" hidden>Confort de lecture</button>'
    ) in page
    assert '<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">' in page


def test_l_icone_est_mc_en_bleu_profond():
    icone = (STATIQUES / "favicon.svg").read_text("utf-8")
    assert ">Mc</text>" in icone
    assert CLAIR["--accent"] in icone


# --- Poids --------------------------------------------------------------------


def test_une_fiche_pese_moins_de_30_ko_html_et_css_compris(client, site_public):
    """Critère du PRD : moins de 30 Ko de HTML et de CSS pour une fiche."""
    html = client.get("/fr/expressions/poser-un-lapin/").content
    poids = len(html) + len(FEUILLE.encode("utf-8"))
    assert poids < 30_000, f"{poids} octets"

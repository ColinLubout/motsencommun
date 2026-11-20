"""Les documents du dépôt : signalement des failles et traductions du README."""

import re
from pathlib import Path

from django.conf import settings

RACINE = Path(settings.BASE_DIR)
SIGNALEMENT_PRIVE = (
    "https://github.com/ColinLubout/motsencommun/security/advisories/new"
)


def test_security_md_renvoie_au_signalement_prive_de_github():
    assert SIGNALEMENT_PRIVE in (RACINE / "SECURITY.md").read_text("utf-8")


def test_le_readme_porte_une_date_de_version():
    assert re.search(
        r"^Version de ce texte : \d{4}-\d{2}-\d{2}", lire("README.md"), re.MULTILINE
    )


def test_chaque_traduction_du_readme_suit_la_convention():
    traductions = sorted(RACINE.glob("README.*.md"))
    assert traductions, "il devrait y avoir au moins README.en.md"
    en_tete = lire("README.md").split("\n## ", 1)[0]
    for traduction in traductions:
        # Code ISO 639-1, ou étiquette BCP 47 pour une variante régionale (pt-BR).
        assert re.fullmatch(r"README\.[a-z]{2}(-[A-Z]{2})?\.md", traduction.name)
        premiere_ligne = traduction.read_text("utf-8").splitlines()[0]
        assert "README.md" in premiere_ligne
        assert re.search(r"\d{4}-\d{2}-\d{2}", premiere_ligne)
        assert f"]({traduction.name})" in en_tete, (
            f"{traduction.name} absent du haut de README.md"
        )


def lire(nom):
    return (RACINE / nom).read_text("utf-8")

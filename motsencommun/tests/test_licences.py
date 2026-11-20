"""Le dépôt contient la licence du code (MIT) et celle des données (CC BY 4.0)."""

from pathlib import Path

from django.conf import settings

RACINE = Path(settings.BASE_DIR)


def test_le_code_est_sous_licence_mit():
    texte = (RACINE / "LICENCE-CODE").read_text("utf-8")
    assert texte.startswith("MIT License")
    assert "Permission is hereby granted, free of charge" in texte


def test_les_donnees_sont_sous_licence_cc_by_4():
    texte = (RACINE / "LICENCE-DONNEES").read_text("utf-8")
    assert texte.startswith("Attribution 4.0 International")
    assert "Section 4 -- Sui Generis Database Rights." in texte
    assert "Creative Commons may be contacted at creativecommons.org." in texte

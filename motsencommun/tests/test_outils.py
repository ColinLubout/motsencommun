"""Le script qui prépare un poste Windows reste cohérent avec le reste du dépôt."""

import re
from pathlib import Path

from django.conf import settings

RACINE = Path(settings.BASE_DIR)
SCRIPT = RACINE / "outils" / "preparer-poste-windows.ps1"


def test_le_script_est_en_utf8_avec_bom():
    """Windows PowerShell 5.1 lit un script sans BOM en ANSI : les accents seraient abîmés."""
    assert SCRIPT.read_bytes().startswith(b"\xef\xbb\xbf")


def test_le_script_installe_la_meme_version_de_uv_que_l_integration_continue():
    version = re.search(
        r'\$VersionUv = "([\d.]+)"', SCRIPT.read_text("utf-8-sig")
    ).group(1)
    workflow = (RACINE / ".github" / "workflows" / "verifications.yml").read_text(
        "utf-8"
    )
    versions_ci = set(re.findall(r'version: "([\d.]+)"', workflow))
    assert versions_ci == {version}


def test_le_script_installe_de_quoi_compiler_pyicu():
    """PyICU se compile à l'installation : il lui faut ICU, pkg-config et un compilateur C++."""
    paquets = re.search(r'paquets="([^"]+)"', SCRIPT.read_text("utf-8-sig")).group(1)
    assert {"libicu-dev", "pkg-config", "g++"} <= set(paquets.split())

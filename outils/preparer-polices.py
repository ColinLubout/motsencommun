"""Prépare les polices du site dans static/polices/, à partir de leurs versions publiées.

À lancer à la racine du dépôt, seulement pour changer de version de police :

    uv run --no-project --with fonttools==4.68.0 --with brotli==1.2.1 python outils/preparer-polices.py

- Literata 3.103 (SIL OFL 1.1, sans nom réservé) : la police variable est figée
  à la taille optique du texte (opsz 12) et à la plage de graisses du site
  (400 à 700), puis découpée en deux fichiers WOFF2, latin et cyrillique : un
  navigateur ne télécharge que celui dont la page a besoin.
- OpenDyslexic v0.91.12 (SIL OFL 1.1) : son nom est réservé, et la licence
  interdit de le garder à une version modifiée. Les fichiers WOFF2 publiés par
  l'autrice sont donc copiés tels quels, sans découpage.

Chaque téléchargement est vérifié par son empreinte SHA-256 avant usage.
"""

import hashlib
import io
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

DESTINATION = Path(__file__).resolve().parent.parent / "static" / "polices"

LITERATA = (
    "https://github.com/googlefonts/literata/releases/download/3.103/3.103.zip",
    "f7fb973cafb26cf785cbebaeaf51c18f87c15a3bcf4d82a7d4857564db5b056d",
)
LITERATA_DANS_L_ARCHIVE = "fonts/variable/Literata[opsz,wght].ttf"
LITERATA_LICENCE = (
    "OFL.txt",
    "8742963604cd89dc81437811a850018fc03b2bfad686d7422c8235967c87614e",
)

OPENDYSLEXIC = "https://raw.githubusercontent.com/antijingoist/opendyslexic/v0.91.12/"
OPENDYSLEXIC_FICHIERS = {
    "compiled/OpenDyslexic-Regular.woff2": (
        "OpenDyslexic-Regular.woff2",
        "f007004af3cda5d8076e57c943f8cc8d00a0da25988b1ae1048683d60e7cac1a",
    ),
    "compiled/OpenDyslexic-Bold.woff2": (
        "OpenDyslexic-Bold.woff2",
        "dd9fa9c7991113b0dddefe9506a30ad26b48e302b7a8fb91719a4726e8fde85b",
    ),
    "OFL.txt": (
        "OFL-OpenDyslexic.txt",
        "caafcccfb70fc72458fcbda812ec8f0a06cb300cbabb87eabbb30b946124394b",
    ),
}

#: Plages Unicode de chaque fichier Literata (latin avec le latin étendu du polonais…).
PLAGES = {
    "literata-latin.woff2": (
        "U+0000-00FF,U+0100-024F,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,"
        "U+02DC,U+0300-0308,U+0327-0329,U+1E00-1EFF,U+2000-206F,U+20AC,U+2122,"
        "U+2190-2193,U+2212,U+2215,U+FEFF,U+FFFD"
    ),
    "literata-cyrillique.woff2": (
        "U+0301,U+0400-052F,U+1C80-1C8A,U+20B4,U+2116,U+2DE0-2DFF,U+A640-A69F"
    ),
}


def telecharger(adresse, empreinte):
    """Le contenu de ``adresse``, seulement si son SHA-256 est celui attendu."""
    print(f"Téléchargement de {adresse}")
    with urllib.request.urlopen(adresse, timeout=60) as reponse:  # noqa: S310 (adresses fixes, en HTTPS)
        contenu = reponse.read()
    obtenue = hashlib.sha256(contenu).hexdigest()
    if obtenue != empreinte:
        sys.exit(
            f"Empreinte inattendue pour {adresse} : {obtenue}. Rien n'a été écrit."
        )
    return contenu


def fonttools(*arguments):
    subprocess.run([sys.executable, "-m", "fontTools", *arguments], check=True)  # noqa: S603


def main():
    archive = zipfile.ZipFile(io.BytesIO(telecharger(*LITERATA)))
    with tempfile.TemporaryDirectory() as temporaire:
        dossier = Path(temporaire)
        variable = dossier / "Literata.ttf"
        variable.write_bytes(archive.read(LITERATA_DANS_L_ARCHIVE))
        licence = archive.read(LITERATA_LICENCE[0])
        if hashlib.sha256(licence).hexdigest() != LITERATA_LICENCE[1]:
            sys.exit(
                "La licence de Literata n'est pas celle attendue. Rien n'a été écrit."
            )

        instance = dossier / "Literata-texte.ttf"
        fonttools(
            "varLib.instancer",
            str(variable),
            "opsz=12",
            "wght=400:700",
            "-o",
            str(instance),
        )
        resultats = {}
        for nom, plage in PLAGES.items():
            sortie = dossier / nom
            fonttools(
                "subset",
                str(instance),
                f"--unicodes={plage}",
                "--layout-features=*",
                "--flavor=woff2",
                f"--output-file={sortie}",
            )
            resultats[nom] = sortie.read_bytes()
        resultats["OFL-Literata.txt"] = licence
        for chemin, (nom, empreinte) in OPENDYSLEXIC_FICHIERS.items():
            resultats[nom] = telecharger(OPENDYSLEXIC + chemin, empreinte)

        if DESTINATION.exists():
            shutil.rmtree(DESTINATION)
        DESTINATION.mkdir(parents=True)
        for nom, contenu in sorted(resultats.items()):
            (DESTINATION / nom).write_bytes(contenu)
            print(f"  {nom} : {len(contenu) // 1024} Ko")


if __name__ == "__main__":
    main()

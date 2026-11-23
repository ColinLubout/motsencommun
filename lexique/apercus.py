"""Images d'aperçu des fiches (Open Graph) : 1200 × 630 px, dessinées sur ce serveur.

Quand une fiche est partagée dans une messagerie, l'aperçu montre sa vedette et
son sens, en Literata sur bleu profond, avec le nom du site. L'image est
dessinée quand l'entrée est enregistrée, puis servie comme un simple fichier
(par Caddy, sous /media/apercus/). Rien n'est demandé à un autre site.

Seules les entrées relues ont une image : une entrée qui cesse d'être publique
perd la sienne, car Caddy sert ces fichiers sans demander à Django, et rien de
ce qui n'est pas relu ne doit être lisible en ligne.

Le nom du fichier porte une empreinte du texte dessiné (``slug.empreinte.png``) :
quand le texte change, l'adresse change, et les messageries ne gardent pas
l'ancienne image.
"""

import hashlib
import io
import os
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

from lexique import affichage as a

LARGEUR, HAUTEUR = 1200, 630
MARGE = 80
FOND = (0x1C, 0x3D, 0x8F)  # le bleu profond du site
TEXTE = (0xFB, 0xFA, 0xF7)  # le blanc cassé du site
TEXTE_DISCRET = (0xD9, 0xE1, 0xF5)
POLICE = Path(settings.BASE_DIR) / "static" / "polices" / "literata-latin.woff2"

#: Tailles essayées pour la vedette, de la plus grande à la plus petite.
TAILLES_DE_LA_VEDETTE = (76, 68, 60, 52, 46)
LIGNES_DE_LA_VEDETTE = 2
TAILLE_DU_SENS = 38
TAILLE_DU_PIED = 34

#: Changer cette valeur redessine toutes les images (nouvelle mise en page).
VERSION = "1"
SOUS_DOSSIER = "apercus"


@lru_cache(maxsize=16)
def police(taille, graisse=400):
    """Literata à cette taille et cette graisse (400 normal, 700 gras)."""
    resultat = ImageFont.truetype(str(POLICE), taille)
    resultat.set_variation_by_axes([graisse])
    return resultat


def dossier():
    return Path(settings.MEDIA_ROOT) / SOUS_DOSSIER


def textes(entree):
    """(vedette avec sa précision, sens au niveau de l'entrée, niveau)."""
    _niveau, sens = a.version_au_niveau(entree.sens(), entree.niveau)
    return str(entree), sens, entree.niveau


def empreinte(entree):
    contenu = "\n".join((VERSION, *textes(entree)))
    return hashlib.sha256(contenu.encode()).hexdigest()[:12]


def nom_du_fichier(entree):
    return f"{entree.slug}.{empreinte(entree)}.png"


def fichiers_de(slug):
    """Les images de cette entrée. Un slug n'a jamais de point : « lapin.* » ne vise pas « lapin-x.* »."""
    return list(dossier().glob(f"{slug}.*.png"))


def adresse(entree):
    """L'adresse de l'image de l'entrée (relative), ou None si elle n'en a pas."""
    if not a.est_public(entree):
        return None
    nom = nom_du_fichier(entree)
    if not (dossier() / nom).exists():
        return None
    return f"{settings.MEDIA_URL}{SOUS_DOSSIER}/{nom}"


def couper(texte, police_, largeur, lignes_max):
    """Le texte en lignes d'au plus ``largeur`` pixels ; « … » si tout ne tient pas."""
    lignes = []
    for mot in texte.split():
        if lignes and police_.getlength(f"{lignes[-1]} {mot}") <= largeur:
            lignes[-1] = f"{lignes[-1]} {mot}"
        else:
            lignes.append(mot)
    if len(lignes) <= lignes_max:
        return lignes
    lignes = lignes[:lignes_max]
    derniere = lignes[-1]
    while derniere and police_.getlength(f"{derniere} …") > largeur:
        derniere = derniere.rsplit(" ", 1)[0] if " " in derniere else derniere[:-1]
    lignes[-1] = f"{derniere} …"
    return lignes


def dessiner(entree):
    """L'image PNG de l'entrée, en octets."""
    vedette, sens, niveau = textes(entree)
    image = Image.new("RGB", (LARGEUR, HAUTEUR), FOND)
    dessin = ImageDraw.Draw(image)
    largeur = LARGEUR - 2 * MARGE

    for taille in TAILLES_DE_LA_VEDETTE:
        grande = police(taille, 700)
        lignes = couper(vedette, grande, largeur, LIGNES_DE_LA_VEDETTE)
        if not lignes[-1].endswith("…"):
            break
    y = MARGE
    for ligne in lignes:
        dessin.text((MARGE, y), ligne, font=grande, fill=TEXTE)
        y += round(taille * 1.2)

    pied = HAUTEUR - MARGE - TAILLE_DU_PIED
    y += 24
    texte_du_sens = police(TAILLE_DU_SENS)
    hauteur_de_ligne = round(TAILLE_DU_SENS * 1.35)
    place = max(0, (pied - 32 - y) // hauteur_de_ligne)
    for ligne in couper(sens, texte_du_sens, largeur, place) if place else []:
        dessin.text((MARGE, y), ligne, font=texte_du_sens, fill=TEXTE_DISCRET)
        y += hauteur_de_ligne

    dessin.line((MARGE, pied - 20, LARGEUR - MARGE, pied - 20), fill=TEXTE_DISCRET)
    nom_du_site = police(TAILLE_DU_PIED, 700)
    dessin.text((MARGE, pied), "Mots en commun", font=nom_du_site, fill=TEXTE)
    largeur_du_niveau = nom_du_site.getlength(niveau)
    dessin.text(
        (LARGEUR - MARGE - largeur_du_niveau, pied),
        niveau,
        font=nom_du_site,
        fill=TEXTE,
    )

    tampon = io.BytesIO()
    image.save(tampon, format="PNG", optimize=True)
    return tampon.getvalue()


def ecrire(chemin, octets):
    """Écrit le fichier d'un coup : Caddy ne sert jamais une image à moitié écrite."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    provisoire = chemin.with_name(f".{chemin.name}.provisoire")
    provisoire.write_bytes(octets)
    os.replace(provisoire, chemin)


def mettre_a_jour(entree):
    """Dessine l'image d'une entrée relue s'il le faut ; efface celles qui ne servent plus."""
    anciens = fichiers_de(entree.slug)
    if a.est_public(entree):
        cible = dossier() / nom_du_fichier(entree)
        if not cible.exists():
            ecrire(cible, dessiner(entree))
        anciens = [fichier for fichier in anciens if fichier != cible]
    for fichier in anciens:
        fichier.unlink(missing_ok=True)


def effacer(slug):
    for fichier in fichiers_de(slug):
        fichier.unlink(missing_ok=True)

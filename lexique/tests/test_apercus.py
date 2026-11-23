"""Images d'aperçu (Open Graph) : dessinées pour les entrées relues, et seulement elles."""

import io
import re

import pytest
from django.conf import settings
from django.core.management import call_command
from PIL import Image

from lexique import apercus
from lexique.tests.conftest import creer_entree, modifier, relire, rendre_public


@pytest.fixture
def apres_validation(django_capture_on_commit_callbacks):
    """Exécute ce qui attend la fin de la transaction (les images sont dessinées là)."""

    def executer(action, *args, **kwargs):
        with django_capture_on_commit_callbacks(execute=True):
            return action(*args, **kwargs)

    return executer


def images():
    return sorted(fichier.name for fichier in apercus.dossier().glob("*.png"))


def test_une_entree_relue_recoit_son_image(
    db, proprietaire, relecteur, apres_validation
):
    """Critère du PRD : chaque entrée relue a une image 1200 × 630."""
    entree = apres_validation(creer_entree, proprietaire)
    assert images() == [], "un brouillon n'a pas d'image"

    apres_validation(relire, entree, relecteur)
    entree.refresh_from_db()
    assert entree.statut == "relu"
    [nom] = images()
    assert re.fullmatch(r"poser-un-lapin\.[0-9a-f]{12}\.png", nom)
    image = Image.open(apercus.dossier() / nom)
    assert image.format == "PNG"
    assert image.size == (1200, 630)
    assert image.getpixel((5, 5)) == apercus.FOND
    assert len(image.getcolors(maxcolors=100_000)) > 10, "du texte est dessiné"


def test_l_image_disparait_quand_l_entree_n_est_plus_publique(
    db, proprietaire, relecteur, apres_validation
):
    """Caddy sert les images sans Django : une entrée renvoyée en relecture perd la sienne."""
    entree = apres_validation(creer_entree, proprietaire)
    apres_validation(relire, entree, relecteur)
    entree.refresh_from_db()
    assert len(images()) == 1
    apres_validation(modifier, entree, proprietaire, sens_b1="Un sens corrigé.")
    entree.refresh_from_db()
    assert entree.statut == "en_relecture"
    assert images() == []


def test_un_nouveau_texte_donne_une_nouvelle_adresse(
    db, proprietaire, relecteur, tuteur, apres_validation
):
    entree = apres_validation(creer_entree, proprietaire)
    apres_validation(relire, entree, relecteur)
    [avant] = images()
    entree.refresh_from_db()
    apres_validation(modifier, entree, proprietaire, sens_b1="Un sens corrigé.")
    apres_validation(relire, entree, tuteur)
    [apres] = images()
    assert apres != avant, "les messageries ne gardent pas l'ancienne image"


def test_l_image_disparait_avec_l_entree(db, proprietaire, apres_validation):
    entree = creer_entree(proprietaire)
    rendre_public(entree)
    apercus.mettre_a_jour(entree)
    assert len(images()) == 1
    apres_validation(entree.delete)
    assert images() == []


def test_la_fiche_mene_a_son_image(client, site_public):
    """Critère du PRD : la fiche porte les balises Open Graph qui mènent à l'image."""
    apercus.mettre_a_jour(site_public.lapin)
    contenu = client.get("/fr/expressions/poser-un-lapin/").content.decode()
    adresse = re.search(r'<meta property="og:image" content="([^"]*)">', contenu).group(
        1
    )
    [nom] = images()
    assert adresse == f"http://testserver{settings.MEDIA_URL}apercus/{nom}"
    assert '<meta property="og:image:width" content="1200">' in contenu
    assert '<meta property="og:image:height" content="630">' in contenu
    assert '<meta name="twitter:card" content="summary_large_image">' in contenu


def test_pas_d_image_pas_de_balise(client, site_public):
    contenu = client.get("/fr/expressions/poser-un-lapin/").content.decode()
    assert "og:image" not in contenu


def test_l_apercu_d_un_relecteur_ne_mene_a_aucune_image(client_relecteur, site_public):
    apercus.mettre_a_jour(site_public.secrete)
    assert images() == []
    contenu = client_relecteur.get(
        "/fr/expressions/expression-secrete/"
    ).content.decode()
    assert "og:image" not in contenu


def test_une_image_oubliee_ne_rend_pas_un_brouillon_partageable(
    client_relecteur, site_public
):
    """Une modification en masse peut laisser un fichier : la fiche d'un brouillon n'y mène pas."""
    apercus.mettre_a_jour(site_public.lapin)
    rendre_public(site_public.lapin, statut="en_relecture")  # sans enregistrer l'entrée
    assert len(images()) == 1
    contenu = client_relecteur.get("/fr/expressions/poser-un-lapin/").content.decode()
    assert "Pas encore relu" in contenu
    assert "og:image" not in contenu


def test_un_long_sens_est_coupe_proprement():
    police = apercus.police(apercus.TAILLE_DU_SENS)
    lignes = apercus.couper("mot " * 200, police, 1040, 4)
    assert len(lignes) == 4
    assert lignes[-1].endswith(" …")
    assert all(police.getlength(ligne) <= 1040 for ligne in lignes)


def test_une_longue_vedette_est_dessinee(db, proprietaire):
    entree = creer_entree(
        proprietaire,
        vedette="une expression vraiment très longue " * 4,
        sens_b1="Un sens lui aussi très long, " * 20,
    )
    image = Image.open(io.BytesIO(apercus.dessiner(entree)))
    assert image.size == (1200, 630)


def test_generer_apercus_remet_tout_en_ordre(db, site_public, proprietaire):
    """Après une modification en masse : les entrées relues ont leur image, les autres non."""
    rendre_public(site_public.secrete)
    apercus.mettre_a_jour(site_public.secrete)
    rendre_public(site_public.secrete, statut="brouillon")
    apercus.dossier().joinpath("entree-supprimee.0123456789ab.png").write_bytes(b"")
    sortie = io.StringIO()
    call_command("generer_apercus", stdout=sortie)
    noms = images()
    assert [nom.split(".")[0] for nom in noms] == [
        "etre-dans-la-lune",
        "poser-un-lapin",
    ]
    assert "2 entrées relues" in sortie.getvalue()
    assert "1 image(s)" in sortie.getvalue()

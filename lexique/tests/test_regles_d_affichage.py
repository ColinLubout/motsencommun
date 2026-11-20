"""Règles d'affichage : seul le contenu relu est public ; les relecteurs voient le reste."""

import pytest

from lexique import models as m
from lexique.tests.conftest import (
    creer_compte,
    creer_entree,
    creer_exemple,
    creer_piege,
    rendre_public,
)

PAGES_DE_LISTE = [
    "/fr/",
    "/fr/expressions/",
    "/fr/niveau/b1/",
    "/fr/type/sens-figure/",
    "/fr/theme/relations/",
    "/fr/recherche/?q=lapin",
    "/fr/recherche/?q=secrete",
]


def page(client, adresse):
    reponse = client.get(adresse)
    assert reponse.status_code == 200, adresse
    return reponse.content.decode()


# --- Visiteurs ----------------------------------------------------------------


@pytest.mark.parametrize("adresse", PAGES_DE_LISTE)
def test_le_contenu_non_relu_n_apparait_dans_aucune_liste(client, site_public, adresse):
    """Critère du PRD : rien de ce qui n'est pas relu ou validé n'est public."""
    assert "expression secrète" not in page(client, adresse)


def test_une_fiche_ne_montre_que_ce_qui_est_relu(client, site_public):
    fiche = page(client, "/fr/expressions/poser-un-lapin/")
    assert "Sens figuré" in fiche
    assert "Faux ami" not in fiche, "le piège non relu"
    assert "Une explication pas encore relue." not in fiche
    assert "Il <mark>" in fiche
    assert "Une phrase pas encore relue" not in fiche, "l'exemple non relu"
    assert "être dans la lune" in fiche, "le lien vers une entrée relue"
    assert "expression secrète" not in fiche, "le lien vers une entrée non relue"
    assert "Pas encore relu" not in fiche
    assert 'name="robots"' not in fiche


def test_une_traduction_non_relue_n_apparait_pas(client, site_public):
    fiche = page(client, "/en/expressions/poser-un-lapin/")
    assert "to stand someone up" in fiche
    rendre_public(site_public.traduction, statut="en_relecture")
    assert "to stand someone up" not in page(client, "/en/expressions/poser-un-lapin/")
    assert "poser un lapin" not in page(client, "/en/recherche/?q=stand+someone")


@pytest.mark.parametrize("statut", ["brouillon", "en_relecture", "refuse", "retire"])
def test_une_entree_non_publique_repond_404(client, site_public, statut):
    rendre_public(site_public.secrete, statut=statut)
    reponse = client.get("/fr/expressions/expression-secrete/")
    assert reponse.status_code == 404
    assert "Page introuvable" in reponse.content.decode()


def test_validee_est_publique_aussi(client, site_public):
    rendre_public(site_public.secrete, statut="valide")
    assert "expression secrète" in page(client, "/fr/expressions/")


def test_seuls_les_contributeurs_de_contenu_public_sont_credites(client, site_public):
    discret = creer_compte("discret")
    creer_entree(discret, vedette="rien de public", sens_b1="Brouillon.")
    credits = page(client, "/fr/a-propos/")
    assert "<li>proprietaire</li>" in credits
    assert "discret" not in credits


# --- Relecteurs ---------------------------------------------------------------


def test_un_relecteur_voit_une_entree_non_relue_avec_un_bandeau(
    client_relecteur, site_public
):
    """Critère du PRD : connectés, les relecteurs voient le bandeau « Pas encore relu »."""
    fiche = page(client_relecteur, "/fr/expressions/expression-secrete/")
    assert '<p class="bandeau-brouillon" role="status">' in fiche
    assert "Pas encore relu" in fiche
    assert '<meta name="robots" content="noindex">' in fiche


def test_un_relecteur_voit_les_pieges_et_exemples_a_relire(
    client_relecteur, site_public
):
    fiche = page(client_relecteur, "/fr/expressions/poser-un-lapin/")
    assert "Une explication pas encore relue." in fiche
    assert "Une phrase pas encore relue" in fiche
    assert "expression secrète" in fiche
    assert fiche.count('<p class="pas-encore-relu">Pas encore relu</p>') == 2
    assert '<meta name="robots" content="noindex">' in fiche


def test_meme_un_relecteur_ne_voit_pas_ce_qui_est_refuse_ou_retire(
    client_relecteur, site_public
):
    rendre_public(site_public.piege_cache, statut="refuse")
    rendre_public(site_public.exemple_cache, statut="retire")
    fiche = page(client_relecteur, "/fr/expressions/poser-un-lapin/")
    assert "Une explication pas encore relue." not in fiche
    assert "Une phrase pas encore relue" not in fiche


def test_le_proprietaire_voit_les_brouillons(client_proprietaire, site_public):
    assert "Pas encore relu" in page(
        client_proprietaire, "/fr/expressions/expression-secrete/"
    )


def test_un_superutilisateur_sans_double_authentification_ne_voit_rien(
    client, site_public, proprietaire
):
    client.force_login(proprietaire)
    assert client.get("/fr/expressions/expression-secrete/").status_code == 404


def test_un_compte_ordinaire_ne_voit_rien(client, site_public):
    client.force_login(creer_compte("lectrice"))
    assert client.get("/fr/expressions/expression-secrete/").status_code == 404


def test_les_listes_restent_publiques_meme_pour_les_relecteurs(
    client_relecteur, site_public
):
    assert "expression secrète" not in page(client_relecteur, "/fr/expressions/")


# --- Texte des contributeurs ----------------------------------------------------

SCRIPT = "<script>alert(1)</script>"


def test_le_texte_des_contributeurs_reste_echappe_sur_les_pages_publiques(
    client, db, proprietaire
):
    """Critère du PRD : <script> dans chaque champ de texte reste échappé partout."""
    proprietaire.contributeur.nom_affiche = SCRIPT
    proprietaire.contributeur.save()
    theme = m.Theme.objects.create(slug="piege", nom=SCRIPT)
    entree = creer_entree(
        proprietaire,
        slug="xss",
        vedette=SCRIPT,
        precision=SCRIPT,
        api=SCRIPT,
        sens_b1=SCRIPT,
        sens_litteral=SCRIPT,
        formes=[SCRIPT],
    )
    entree.themes.add(theme)
    piege = creer_piege(
        entree,
        proprietaire,
        type_piege="faux_ami",
        langue_apprenant="en",
        declencheur=SCRIPT,
        explication_b1=SCRIPT,
        incorrect=SCRIPT,
        correct=SCRIPT,
    )
    exemple = creer_exemple(
        entree, proprietaire, phrase=f"{SCRIPT} et la suite", surlignage=SCRIPT
    )
    cible = creer_entree(proprietaire, slug="cible", vedette=f"cible {SCRIPT}")
    m.LienEntree.objects.create(entree=entree, cible=cible, type_lien="voir_aussi")
    traductions = [
        m.EntreeTraduction.objects.create(
            entree=entree,
            langue="en",
            sens=SCRIPT,
            sens_litteral=SCRIPT,
            ajoute_par=proprietaire,
        ),
        m.PiegeTraduction.objects.create(
            piege=piege, langue="en", explication=SCRIPT, ajoute_par=proprietaire
        ),
        m.ExempleTraduction.objects.create(
            exemple=exemple, langue="en", traduction=SCRIPT, ajoute_par=proprietaire
        ),
    ]
    m.ThemeTraduction.objects.create(theme=theme, langue="en", nom=SCRIPT)
    rendre_public(entree, piege, exemple, cible, *traductions)

    adresses = [
        "/fr/",
        "/fr/expressions/",
        "/fr/expressions/xss/",
        "/en/expressions/xss/",
        "/fr/theme/piege/",
        "/en/theme/piege/",
        "/fr/type/faux-ami/",
        "/fr/recherche/?q=script",
        f"/fr/recherche/?q={SCRIPT}",
        "/fr/a-propos/",
    ]
    for adresse in adresses:
        contenu = page(client, adresse)
        assert SCRIPT not in contenu, adresse
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in contenu, adresse

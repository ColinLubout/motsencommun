"""Pages publiques : langues, listes et filtres, raccourcis, fiche, Mon niveau, recherche."""

import re

import pytest
from django.test import override_settings

from lexique import affichage as a
from lexique import models as m
from lexique.tests.conftest import (
    SENS_POLONAIS,
    SENS_UKRAINIEN,
    creer_entree,
    creer_exemple,
    creer_piege,
    rendre_public,
)


def html(client, adresse, **entetes):
    reponse = client.get(adresse, **entetes)
    assert reponse.status_code == 200, adresse
    return reponse.content.decode()


def vedettes(page):
    """Les vedettes des entrées listées, dans l'ordre."""
    return re.findall(r'<p class="vedette"><a href="[^"]*" lang="fr">([^<]*)</a>', page)


PAGES = [
    "",
    "expressions/",
    "niveau/b1/",
    "type/sens-figure/",
    "theme/relations/",
    "expressions/poser-un-lapin/",
    "recherche/?q=lapin",
    "telecharger/",
    "a-propos/",
]


# --- Langues ------------------------------------------------------------------


@pytest.mark.parametrize("chemin", PAGES)
def test_chaque_page_existe_en_francais_et_en_anglais(client, site_public, chemin):
    """Critère du PRD : les pages marchent en français, et l'interface existe en anglais."""
    francais = html(client, f"/fr/{chemin}")
    anglais = html(client, f"/en/{chemin}")
    assert '<html lang="fr" dir="ltr">' in francais
    assert '<html lang="en" dir="ltr">' in anglais
    assert "Toutes les expressions" in francais
    assert "All expressions" in anglais
    assert "Toutes les expressions" not in anglais


def test_en_anglais_les_vocabulaires_sont_traduits(client, site_public):
    page = html(client, "/en/expressions/poser-un-lapin/")
    assert "Verb phrase" in page
    assert "Informal" in page
    assert "Figurative meaning" in page
    assert "Level B1" in page


def test_la_racine_mene_au_francais_quel_que_soit_le_navigateur(client, db):
    for entetes in ({}, {"HTTP_ACCEPT_LANGUAGE": "en"}):
        reponse = client.get("/", **entetes)
        assert reponse.status_code == 302
        assert reponse["Location"] == "/fr/"
        assert not reponse.has_header("Vary"), "la redirection ne dépend de rien"


def test_la_langue_ne_vient_que_de_l_adresse(client, site_public):
    client.cookies["django_language"] = "en"
    page = html(client, "/fr/expressions/", HTTP_ACCEPT_LANGUAGE="en")
    assert '<html lang="fr"' in page
    assert "Toutes les expressions" in page


def test_changer_de_langue_est_un_lien_vers_la_meme_page(client, site_public):
    page = html(client, "/fr/expressions/poser-un-lapin/?mon_niveau=A2")
    assert (
        '<a href="/en/expressions/poser-un-lapin/?mon_niveau=A2" hreflang="en" lang="en">'
        "English</a>"
    ) in page
    assert 'hreflang="fr" lang="fr" aria-current="true">Français</a>' in page


@pytest.mark.parametrize("chemin", PAGES)
def test_le_pied_de_page_nomme_la_licence_et_mene_aux_credits(
    client, site_public, chemin
):
    page = html(client, f"/fr/{chemin}")
    assert "CC BY 4.0" in page
    assert 'href="/fr/a-propos/#contributeurs"' in page


# --- Liste, filtres et raccourcis ---------------------------------------------


@pytest.fixture
def lexique_a_filtrer(db, proprietaire):
    emotions = m.Theme.objects.create(slug="emotions", nom="Émotions")
    entrees = {}
    for vedette, niveau, registre, type_piege, theme in [
        ("avoir le cafard", "B1", "familier", "sens_figure", emotions),
        ("être aux anges", "B1", "courant", "sens_figure", emotions),
        ("actuellement", "B1", "familier", "faux_ami", emotions),
        ("en avoir marre", "A2", "familier", "sens_figure", emotions),
        ("kiffer", "B1", "familier", "sens_figure", None),
    ]:
        entree = creer_entree(
            proprietaire, vedette=vedette, niveau=niveau, registre=registre
        )
        piege = creer_piege(entree, proprietaire, type_piege=type_piege)
        if theme:
            entree.themes.add(theme)
        rendre_public(entree, piege)
        entrees[vedette] = entree
    return entrees


def test_les_filtres_se_combinent(client, lexique_a_filtrer):
    """Critère du PRD : niveau, type de piège, thème et registre se combinent."""
    adresse = (
        "/fr/expressions/?niveau=B1&type=sens_figure&theme=emotions&registre=familier"
    )
    page = html(client, adresse)
    assert vedettes(page) == ["avoir le cafard"]
    for selectionne in (
        '<option value="B1" selected>',
        '<option value="sens_figure" selected>',
        '<option value="emotions" selected>',
        '<option value="familier" selected>',
    ):
        assert selectionne in page, "le formulaire reproduit la même liste"
    assert vedettes(html(client, adresse)) == ["avoir le cafard"]


@pytest.mark.parametrize(
    ("parametres", "attendu"),
    [
        ("niveau=A2", ["en avoir marre"]),
        ("type=faux_ami", ["actuellement"]),
        ("type=faux-ami", ["actuellement"]),
        ("registre=courant", ["être aux anges"]),
        (
            "theme=emotions&niveau=B1",
            ["actuellement", "avoir le cafard", "être aux anges"],
        ),
        ("niveau=Z9&theme=inconnu", None),
    ],
)
def test_chaque_filtre(client, lexique_a_filtrer, parametres, attendu):
    tous = [
        "actuellement",
        "avoir le cafard",
        "en avoir marre",
        "être aux anges",
        "kiffer",
    ]
    assert vedettes(html(client, f"/fr/expressions/?{parametres}")) == (attendu or tous)


def test_un_type_de_piege_non_relu_ne_compte_pas(
    client, lexique_a_filtrer, proprietaire
):
    creer_piege(lexique_a_filtrer["kiffer"], proprietaire, type_piege="calque")
    assert vedettes(html(client, "/fr/expressions/?type=calque")) == []


@pytest.mark.parametrize(
    ("raccourci", "liste"),
    [
        ("niveau/b1/", "expressions/?niveau=B1"),
        ("type/faux-ami/", "expressions/?type=faux_ami"),
        ("theme/emotions/", "expressions/?theme=emotions"),
    ],
)
def test_un_raccourci_est_la_liste_prefiltree(
    client, lexique_a_filtrer, raccourci, liste
):
    assert vedettes(html(client, f"/fr/{raccourci}")) == vedettes(
        html(client, f"/fr/{liste}")
    )


def test_un_raccourci_porte_un_titre(client, lexique_a_filtrer):
    assert "<h1>Niveau B1</h1>" in html(client, "/fr/niveau/b1/")
    assert "<h1>Faux ami</h1>" in html(client, "/fr/type/faux-ami/")
    assert "<h1>False friend</h1>" in html(client, "/en/type/faux-ami/")
    assert "<h1>Émotions</h1>" in html(client, "/fr/theme/emotions/")


@pytest.mark.parametrize(
    "chemin",
    ["niveau/z9/", "niveau/B1/", "type/faux_ami/", "type/inconnu/", "theme/inconnu/"],
)
def test_un_raccourci_inconnu_repond_404(client, db, chemin):
    assert client.get(f"/fr/{chemin}").status_code == 404


@override_settings(ENTREES_PAR_PAGE=2)
def test_la_liste_est_alphabetique_et_paginee(client, lexique_a_filtrer):
    premiere = html(client, "/fr/expressions/?registre=familier")
    assert vedettes(premiere) == ["actuellement", "avoir le cafard"]
    assert "Page 1 sur 2" in premiere
    assert 'href="?registre=familier&amp;page=2" rel="next"' in premiere
    seconde = html(client, "/fr/expressions/?registre=familier&page=2")
    assert vedettes(seconde) == ["en avoir marre", "kiffer"]
    assert "4 entrées" in seconde


# --- Mon niveau ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("versions", "niveau", "attendu"),
    [
        ({"B1": "b1"}, "A2", ("B1", "b1")),
        ({"A1": "a1", "B1": "b1", "C1": "c1"}, "B2", ("B1", "b1")),
        ({"A1": "a1", "B1": "b1", "C1": "c1"}, "A2", ("A1", "a1")),
        ({"A1": "a1", "B1": "b1", "C1": "c1"}, "C2", ("C1", "c1")),
        ({"B2": "b2", "C1": "c1"}, "A1", ("B2", "b2")),
        ({}, "B1", (None, "")),
    ],
)
def test_version_au_niveau(versions, niveau, attendu):
    assert a.version_au_niveau(versions, niveau) == attendu


def test_mon_niveau_sans_version_a_ce_niveau(client, db, proprietaire):
    """Critère du PRD : une entrée qui n'a que sens_b1, lue au niveau A2."""
    entree = creer_entree(proprietaire, sens_b1="Ne pas venir, sans prévenir.")
    piege = creer_piege(
        entree, proprietaire, explication_b1="Rien à voir avec les lapins."
    )
    rendre_public(entree, piege)
    page = html(client, "/fr/expressions/poser-un-lapin/?mon_niveau=A2")
    assert '<p lang="fr">Ne pas venir, sans prévenir.</p>' in page
    assert "Pas de version de niveau A2 : voici la version B1." in page
    assert '<p lang="fr">Rien à voir avec les lapins.</p>' in page


def test_mon_niveau_choisit_la_version_la_plus_haute_en_dessous(
    client, db, proprietaire
):
    entree = creer_entree(
        proprietaire,
        sens_a1="Version A1.",
        sens_b1="Version B1.",
        sens_c1="Version C1.",
    )
    piege = creer_piege(
        entree,
        proprietaire,
        explication_a2="Piège A2.",
        explication_b1="",
        explication_b2="Piège B2.",
    )
    rendre_public(entree, piege)
    adresse = "/fr/expressions/poser-un-lapin/"
    for niveau, sens, explication in [
        ("B2", "Version B1.", "Piège B2."),
        ("A2", "Version A1.", "Piège A2."),
        ("C2", "Version C1.", "Piège B2."),
        ("", "Version B1.", "Piège A2."),  # le niveau de l'entrée, B1
    ]:
        page = html(client, f"{adresse}?mon_niveau={niveau}")
        assert f'<p lang="fr">{sens}</p>' in page, niveau
        assert f'<p lang="fr">{explication}</p>' in page, niveau
    page = html(client, f"{adresse}?mon_niveau=B2")
    assert "Pas de version de niveau B2 : voici la version B1." in page
    assert re.search(
        r'Autres versions :\s*<a href="\?mon_niveau=A1">A1</a>, '
        r'<a href="\?mon_niveau=C1">C1</a>',
        page,
    )


def test_mon_niveau_ne_filtre_jamais_les_listes(client, lexique_a_filtrer):
    """Décidé le 20 novembre 2026 : « mon_niveau » ne filtre pas, « niveau » filtre."""
    assert len(vedettes(html(client, "/fr/expressions/?mon_niveau=A2"))) == 5


def test_mon_niveau_suit_le_lecteur_de_page_en_page(client, site_public):
    page = html(client, "/fr/expressions/?mon_niveau=A2")
    assert 'href="/fr/expressions/poser-un-lapin/?mon_niveau=A2"' in page
    assert 'href="/fr/a-propos/?mon_niveau=A2"' in page
    assert '<input type="hidden" name="mon_niveau" value="A2">' in page
    assert '<option value="A2" selected>A2</option>' in page


def test_le_formulaire_mon_niveau_garde_les_autres_parametres(
    client, lexique_a_filtrer
):
    page = html(client, "/fr/expressions/?theme=emotions&page=1&mon_niveau=B1")
    formulaire = page[page.index('<form class="mon-niveau"') :]
    formulaire = formulaire[: formulaire.index("</form>")]
    assert '<input type="hidden" name="theme" value="emotions">' in formulaire
    assert 'name="page"' not in formulaire


# --- Fiche --------------------------------------------------------------------


def test_la_fiche_dans_l_ordre_du_prd(client, site_public):
    page = html(client, "/fr/expressions/poser-un-lapin/")
    reperes = [
        "<h1>",
        'id="titre-sens"',
        'id="titre-pieges"',
        'id="titre-exemples"',
        'id="titre-liens"',
        'class="credit"',
    ]
    positions = [page.index(repere) for repere in reperes]
    assert positions == sorted(positions)
    assert "Ajoutée par proprietaire" in page
    assert "statut : Relu" in page


def test_le_surlignage_entoure_exactement_les_mots(client, site_public):
    """Critère du PRD : <mark> autour du texte exact du surlignage."""
    page = html(client, "/fr/expressions/poser-un-lapin/")
    assert '<p lang="fr">Il <mark>m&#x27;a posé un lapin</mark> hier soir.</p>' in page


def test_le_surlignage_reste_echappe(client, db, proprietaire):
    entree = creer_entree(proprietaire)
    exemple = creer_exemple(
        entree,
        proprietaire,
        phrase="Il a écrit <b>lapin</b> & co.",
        surlignage="<b>lapin</b>",
    )
    rendre_public(entree, exemple)
    page = html(client, "/fr/expressions/poser-un-lapin/")
    assert "Il a écrit <mark>&lt;b&gt;lapin&lt;/b&gt;</mark> &amp; co." in page


def test_les_paires_incorrect_correct(client, db, proprietaire):
    entree = creer_entree(proprietaire)
    piege = creer_piege(
        entree, proprietaire, incorrect="Je suis faim.", correct="J'ai faim."
    )
    rendre_public(entree, piege)
    page = html(client, "/fr/expressions/poser-un-lapin/")
    assert '<span aria-hidden="true">✗</span>' in page
    assert '<span lang="fr">Je suis faim.</span>' in page
    assert '<span aria-hidden="true">✓</span>' in page


def test_l_administration_mene_a_la_fiche(site_public):
    assert site_public.lapin.get_absolute_url() == "/fr/expressions/poser-un-lapin/"


# --- Recherche ----------------------------------------------------------------


def test_la_recherche_ignore_accents_et_majuscules(client, db, proprietaire):
    """Critère du PRD, sur la page : « etre en train » trouve « Être en train de »."""
    rendre_public(creer_entree(proprietaire, vedette="Être en train de"))
    page = html(client, "/fr/recherche/?q=etre+en+train")
    assert vedettes(page) == ["Être en train de"]
    assert "1 résultat pour « etre en train »" in page


def test_la_recherche_passe_par_les_traductions_de_la_langue(client, site_public):
    assert vedettes(html(client, "/en/recherche/?q=stand+someone")) == [
        "poser un lapin à qqn"
    ]
    assert vedettes(html(client, "/fr/recherche/?q=stand+someone")) == []


def test_une_recherche_vide(client, site_public):
    page = html(client, "/fr/recherche/")
    assert "Tapez une expression" in page
    assert vedettes(page) == []


# --- Attributs lang et dir ----------------------------------------------------


@override_settings(
    LANGUAGES=[
        ("fr", "Français"),
        ("en", "English"),
        ("uk", "Українська"),
        ("pl", "Polski"),
    ]
)
def test_les_traductions_ukrainiennes_et_polonaises_portent_leur_langue(
    client, entree_multilingue
):
    """Critère du PRD : les traductions de test s'affichent avec le bon attribut lang."""
    exemple = creer_exemple(entree_multilingue, entree_multilingue.ajoute_par)
    traductions = [
        m.ExempleTraduction.objects.create(
            exemple=exemple,
            langue=langue,
            traduction=texte,
            ajoute_par=exemple.ajoute_par,
        )
        for langue, texte in (
            ("uk", "Він мене підвів."),
            ("pl", "Wystawił mnie do wiatru."),
        )
    ]
    rendre_public(
        entree_multilingue, exemple, *entree_multilingue.traductions.all(), *traductions
    )
    for langue, sens, phrase in (
        ("uk", SENS_UKRAINIEN, "Він мене підвів."),
        ("pl", SENS_POLONAIS, "Wystawił mnie do wiatru."),
    ):
        page = html(client, f"/{langue}/expressions/poser-un-lapin/")
        assert f'<span lang="{langue}" dir="ltr">{sens}</span>' in page
        assert f'<p class="traduction" lang="{langue}" dir="ltr">{phrase}</p>' in page
        assert '<p lang="fr">Ne pas venir à un rendez-vous, sans prévenir.</p>' in page


@override_settings(LANGUAGES=[("fr", "Français"), ("ar", "العربية")])
def test_une_traduction_de_droite_a_gauche(client, site_public, proprietaire):
    traduction = m.EntreeTraduction.objects.create(
        entree=site_public.lapin,
        langue="ar",
        sens="لم يأتِ إلى الموعد",
        ajoute_par=proprietaire,
    )
    rendre_public(traduction)
    page = html(client, "/ar/expressions/poser-un-lapin/")
    assert '<html lang="ar" dir="rtl">' in page
    assert '<span lang="ar" dir="rtl">لم يأتِ إلى الموعد</span>' in page
    assert '<p lang="fr">Ne pas venir à un rendez-vous, sans prévenir.</p>' in page

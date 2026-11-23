"""Pages à intégrer : la fiche seule, que les enseignants affichent dans un cours."""

import re

from lexique.tests.conftest import creer_entree, rendre_public

FICHE = "/fr/expressions/poser-un-lapin/"
INTEGRATION = "/fr/expressions/poser-un-lapin/integrer/"


def page(client, adresse):
    reponse = client.get(adresse)
    assert reponse.status_code == 200, adresse
    return reponse.content.decode()


def test_chaque_entree_a_sa_page_a_integrer(client, site_public):
    """Critère du PRD : chaque entrée a une page /integrer/."""
    contenu = page(client, INTEGRATION)
    assert "poser un lapin à qqn" in contenu
    assert "Ne pas venir à un rendez-vous, sans prévenir." in contenu
    assert "Il <mark>m&#x27;a posé un lapin</mark> hier soir." in contenu
    assert "Sens figuré" in contenu
    # Le contenu relu seulement, comme sur la fiche.
    assert "Une explication pas encore relue." not in contenu
    assert "expression secrète" not in contenu
    assert page(client, "/en" + INTEGRATION[3:]).count("to stand someone up") == 1


def test_la_page_a_integrer_n_a_que_la_fiche(client, site_public):
    """Ni navigation, ni recherche, ni formulaire, ni script : la fiche, et un lien vers le site."""
    contenu = page(client, INTEGRATION)
    for absent in ("<nav", "<form", "<script", "bouton-confort", "Mon niveau"):
        assert absent not in contenu, absent
    assert '<meta name="robots" content="noindex">' in contenu
    assert (
        f'<a href="{FICHE}" target="_blank">Voir cette fiche sur Mots en commun</a>'
        in (contenu)
    )


def test_les_liens_d_une_page_integree_s_ouvrent_dans_un_nouvel_onglet(
    client, site_public
):
    """Nos autres pages refusent les cadres : leurs liens quittent le cadre."""
    site_public.lapin.sens_a2 = "Une version A2."
    site_public.lapin.save()
    rendre_public(site_public.lapin)
    contenu = page(client, INTEGRATION)
    liens = re.findall(r"<a\b[^>]*>", contenu)
    vers_le_site = [lien for lien in liens if 'href="/' in lien]
    assert len(vers_le_site) == 3, "thème, entrée liée, et la fiche complète"
    for lien in vers_le_site:
        assert 'target="_blank"' in lien, lien
    # Les autres versions du sens restent dans le cadre.
    autres_versions = [lien for lien in liens if 'href="?mon_niveau=' in lien]
    assert autres_versions
    for lien in autres_versions:
        assert "target" not in lien, lien


def test_la_page_a_integrer_suit_mon_niveau(client, db, proprietaire):
    entree = creer_entree(
        proprietaire, slug="lune", sens_a2="Version A2.", sens_b1="Version B1."
    )
    rendre_public(entree)
    assert "Version A2." in page(client, "/fr/expressions/lune/integrer/?mon_niveau=A2")
    assert "Version B1." in page(client, "/fr/expressions/lune/integrer/")


def test_une_entree_non_relue_n_a_pas_de_page_a_integrer(client, site_public):
    assert client.get("/fr/expressions/expression-secrete/integrer/").status_code == 404


def test_un_relecteur_voit_la_page_a_integrer_d_une_entree_non_relue(
    client_relecteur, site_public
):
    contenu = page(client_relecteur, "/fr/expressions/expression-secrete/integrer/")
    assert "Pas encore relu" in contenu
    assert '<meta name="robots" content="noindex">' in contenu


def test_la_fiche_propose_le_code_a_copier(client, site_public):
    """Critère du PRD : la fiche offre un code <iframe> prêt à copier."""
    contenu = page(client, FICHE)
    assert '<details class="integrer">' in contenu
    assert (
        "&lt;iframe src=&quot;http://testserver/fr/expressions/poser-un-lapin/integrer/&quot; "
        "title=&quot;poser un lapin à qqn — Mots en commun&quot; "
        "width=&quot;100%&quot; height=&quot;500&quot; loading=&quot;lazy&quot;&gt;&lt;/iframe&gt;"
    ) in contenu
    # Le code est du texte à copier : la fiche ne contient aucun vrai cadre.
    assert "<iframe" not in contenu


def test_le_code_a_copier_garde_mon_niveau(client, site_public):
    contenu = page(client, FICHE + "?mon_niveau=A2")
    assert "/fr/expressions/poser-un-lapin/integrer/?mon_niveau=A2&quot;" in contenu


def test_le_code_a_copier_echappe_la_vedette(client, db, proprietaire):
    """Une vedette avec guillemets et chevrons reste du texte, ici et chez l'enseignant."""
    entree = creer_entree(proprietaire, slug="guillemets", vedette='dire "<b>non</b>"')
    rendre_public(entree)
    contenu = page(client, "/fr/expressions/guillemets/")
    # Échappée deux fois : pour l'attribut title, puis pour l'affichage dans la fiche.
    assert (
        "title=&quot;dire &amp;quot;&amp;lt;b&amp;gt;non&amp;lt;/b&amp;gt;&amp;quot;"
        in (contenu)
    )
    assert "<b>non</b>" not in contenu


def test_pas_de_code_a_copier_pour_un_apercu(client_relecteur, site_public):
    contenu = page(client_relecteur, "/fr/expressions/expression-secrete/")
    assert "integrer" not in contenu

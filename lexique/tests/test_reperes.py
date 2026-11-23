"""Être trouvé et bien partagé : adresses canoniques, langues, robots.txt, plan du site."""

import datetime
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from django.conf import settings

from lexique import models as m
from lexique.tests.conftest import creer_entree, creer_piege, rendre_public

FICHE = "/fr/expressions/poser-un-lapin/"
LUNE = "/fr/expressions/etre-dans-la-lune/"


def page(client, adresse):
    reponse = client.get(adresse)
    assert reponse.status_code == 200, adresse
    return reponse.content.decode()


def canonique(contenu):
    adresses = re.findall(r'<link rel="canonical" href="([^"]*)">', contenu)
    assert len(adresses) == 1
    return adresses[0]


def alternatives(contenu):
    return dict(
        re.findall(r'<link rel="alternate" hreflang="([^"]*)" href="([^"]*)">', contenu)
    )


def meta(contenu, nom):
    """La valeur d'une balise <meta name=…> ou <meta property=…>, ou None."""
    trouve = re.search(
        rf'<meta (?:name|property)="{re.escape(nom)}" content="([^"]*)">', contenu
    )
    return trouve.group(1) if trouve else None


# --- Titres et descriptions ---------------------------------------------------


def test_le_titre_et_la_description_d_une_fiche(client, site_public):
    """PRD : « poser un lapin à qqn — Mots en commun », et le sens pour description."""
    contenu = page(client, FICHE)
    assert "<title>poser un lapin à qqn — Mots en commun</title>" in contenu
    assert (
        meta(contenu, "description") == "Ne pas venir à un rendez-vous, sans prévenir."
    )


def test_la_description_suit_la_traduction_relue(client, site_public):
    assert meta(page(client, "/en" + FICHE[3:]), "description") == "to stand someone up"


def test_la_description_ne_depend_pas_de_mon_niveau(client, db, proprietaire):
    entree = creer_entree(proprietaire, slug="lune", sens_a2="En A2.", sens_b1="En B1.")
    rendre_public(entree)
    contenu = page(client, "/fr/expressions/lune/?mon_niveau=A2")
    assert '<p lang="fr">En A2.</p>' in contenu
    assert meta(contenu, "description") == "En B1."


def test_les_autres_pages_ont_la_description_du_site(client, site_public):
    description = meta(page(client, "/fr/expressions/"), "description")
    assert description.startswith("Les expressions françaises qui ne veulent pas dire")
    assert meta(page(client, "/en/"), "description").startswith("French expressions")


# --- Adresse canonique et langues ---------------------------------------------


def test_une_fiche_sans_traduction_relue_renvoie_au_francais(client, site_public):
    """PRD : dans une langue sans traduction relue, la fiche est canonique en français."""
    assert canonique(page(client, "/en" + LUNE[3:])) == "http://testserver" + LUNE
    assert alternatives(page(client, LUNE)) == {}
    assert alternatives(page(client, "/en" + LUNE[3:])) == {}


def test_une_fiche_traduite_declare_ses_langues(client, site_public):
    """PRD : hreflang seulement pour les langues où l'entrée a une traduction relue."""
    francais = page(client, FICHE)
    anglais = page(client, "/en" + FICHE[3:])
    assert canonique(francais) == "http://testserver" + FICHE
    assert canonique(anglais) == "http://testserver/en" + FICHE[3:]
    attendues = {
        "fr": "http://testserver" + FICHE,
        "en": "http://testserver/en" + FICHE[3:],
        "x-default": "http://testserver" + FICHE,
    }
    assert alternatives(francais) == attendues
    assert alternatives(anglais) == attendues


def test_une_traduction_non_relue_ne_compte_pas(client, site_public):
    rendre_public(site_public.traduction, statut="en_relecture")
    assert alternatives(page(client, FICHE)) == {}
    assert canonique(page(client, "/en" + FICHE[3:])) == "http://testserver" + FICHE


def test_une_traduction_dans_une_langue_sans_interface_ne_compte_pas(
    client, site_public, proprietaire
):
    """Le polonais n'a pas encore d'interface (/pl/) : pas de version polonaise à déclarer."""
    traduction = m.EntreeTraduction.objects.create(
        entree=site_public.lune,
        langue="pl",
        sens="Bujać w obłokach.",
        ajoute_par=proprietaire,
    )
    rendre_public(traduction)
    assert alternatives(page(client, LUNE)) == {}


def test_mon_niveau_ne_fait_pas_partie_de_l_adresse_canonique(client, site_public):
    contenu = page(client, FICHE + "?mon_niveau=A2")
    assert canonique(contenu) == "http://testserver" + FICHE
    assert all(
        "mon_niveau" not in adresse for adresse in alternatives(contenu).values()
    )


def test_les_pages_de_l_interface_existent_dans_chaque_langue(client, site_public):
    contenu = page(client, "/fr/expressions/?niveau=B1&mon_niveau=A2")
    assert canonique(contenu) == "http://testserver/fr/expressions/?niveau=B1"
    assert alternatives(contenu) == {
        "fr": "http://testserver/fr/expressions/?niveau=B1",
        "en": "http://testserver/en/expressions/?niveau=B1",
        "x-default": "http://testserver/fr/expressions/?niveau=B1",
    }
    assert canonique(page(client, "/en/a-propos/")) == "http://testserver/en/a-propos/"


def test_une_page_introuvable_n_a_pas_d_adresse_canonique(client, db):
    contenu = client.get("/fr/nulle-part/").content.decode()
    assert 'rel="canonical"' not in contenu
    assert "og:" not in contenu


# --- Aperçus de liens (Open Graph) --------------------------------------------


def test_les_balises_open_graph_d_une_fiche(client, site_public):
    contenu = page(client, FICHE)
    assert meta(contenu, "og:type") == "article"
    assert meta(contenu, "og:title") == "poser un lapin à qqn"
    assert (
        meta(contenu, "og:description")
        == "Ne pas venir à un rendez-vous, sans prévenir."
    )
    assert meta(contenu, "og:url") == "http://testserver" + FICHE
    assert meta(contenu, "og:site_name") == "Mots en commun"


def test_les_balises_open_graph_des_autres_pages(client, site_public):
    contenu = page(client, "/fr/")
    assert meta(contenu, "og:type") == "website"
    assert meta(contenu, "og:title") == "Mots en commun"
    assert meta(contenu, "og:url") == "http://testserver/fr/"
    assert meta(contenu, "og:image") is None


def test_le_texte_des_balises_reste_echappe(client, db, proprietaire):
    entree = creer_entree(
        proprietaire,
        slug="guillemets",
        vedette='dire "non"',
        sens_b1='Un "refus" <b>net</b>.',
    )
    rendre_public(entree)
    contenu = page(client, "/fr/expressions/guillemets/")
    assert meta(contenu, "og:title") == "dire &quot;non&quot;"
    assert (
        meta(contenu, "description") == "Un &quot;refus&quot; &lt;b&gt;net&lt;/b&gt;."
    )


# --- robots.txt ---------------------------------------------------------------


def test_robots_txt_accueille_les_moteurs_et_ecarte_les_robots_d_ia(client, db):
    """Critère du PRD : robots.txt liste les robots d'IA réglés dans les réglages."""
    reponse = client.get("/robots.txt")
    assert reponse.status_code == 200
    assert reponse["Content-Type"] == "text/plain; charset=utf-8"
    texte = reponse.content.decode()
    groupes = [groupe.strip().splitlines() for groupe in texte.split("\n\n")]
    groupes = [[ligne for ligne in g if not ligne.startswith("#")] for g in groupes]
    groupes = [g for g in groupes if g]
    ia, tous, plan = groupes
    assert ia == [
        f"User-agent: {robot}" for robot in settings.ROBOTS_D_ENTRAINEMENT_IA
    ] + ["Disallow: /"]
    assert {"User-agent: GPTBot", "User-agent: ClaudeBot", "User-agent: CCBot"} <= set(
        ia
    )
    assert "User-agent: Google-Extended" in ia
    assert tous == ["User-agent: *", "Disallow:"]
    assert plan == ["Sitemap: http://testserver/sitemap.xml"]
    # La voie prévue pour l'IA : la page de téléchargement.
    assert "http://testserver/fr/telecharger/" in texte


def test_robots_txt_ne_revele_pas_le_chemin_de_l_administration(client, db):
    texte = client.get("/robots.txt").content.decode()
    assert settings.CHEMIN_ADMIN.strip("/") not in texte


def test_robots_txt_suit_les_reglages(client, db, settings):
    settings.ROBOTS_D_ENTRAINEMENT_IA = ["RobotDEssai"]
    texte = client.get("/robots.txt").content.decode()
    assert "User-agent: RobotDEssai\nDisallow: /" in texte
    assert "GPTBot" not in texte


# --- Plan du site -------------------------------------------------------------


def adresses_du_plan(client):
    reponse = client.get("/sitemap.xml")
    assert reponse.status_code == 200
    assert reponse["Content-Type"] == "application/xml; charset=utf-8"
    racine = ET.fromstring(reponse.content)  # noqa: S314 (notre propre plan du site)
    espace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return {
        url.find("s:loc", espace).text: getattr(
            url.find("s:lastmod", espace), "text", None
        )
        for url in racine.findall("s:url", espace)
    }


def test_le_plan_du_site_ne_liste_que_les_entrees_relues(client, site_public):
    """Critère du PRD : sitemap.xml ne liste que les entrées relues."""
    adresses = adresses_du_plan(client)
    assert "http://testserver" + FICHE in adresses
    assert "http://testserver" + LUNE in adresses
    assert not any("expression-secrete" in adresse for adresse in adresses)
    assert not any("integrer" in adresse for adresse in adresses)
    assert adresses[
        "http://testserver" + FICHE
    ] == site_public.lapin.modifie_le.strftime("%Y-%m-%d")


def test_le_plan_du_site_suit_les_regles_des_langues(client, site_public):
    adresses = adresses_du_plan(client)
    # Traduite en anglais : la fiche anglaise est canonique, donc listée.
    assert "http://testserver/en" + FICHE[3:] in adresses
    # Sans traduction anglaise : seule la version française.
    assert "http://testserver/en" + LUNE[3:] not in adresses
    for langue in ("fr", "en"):
        assert f"http://testserver/{langue}/" in adresses
        assert f"http://testserver/{langue}/expressions/" in adresses
        assert f"http://testserver/{langue}/telecharger/" in adresses
        assert f"http://testserver/{langue}/a-propos/" in adresses


def test_le_plan_du_site_liste_les_raccourcis_qui_ont_des_entrees(client, site_public):
    adresses = adresses_du_plan(client)
    assert "http://testserver/fr/niveau/b1/" in adresses
    assert "http://testserver/fr/niveau/a2/" in adresses
    assert "http://testserver/fr/niveau/c2/" not in adresses
    assert "http://testserver/fr/type/sens-figure/" in adresses
    assert "http://testserver/fr/type/faux-ami/" not in adresses, "piège non relu"
    assert "http://testserver/fr/theme/relations/" in adresses
    assert "http://testserver/fr/theme/temps/" in adresses


@pytest.mark.parametrize("statut", ["brouillon", "en_relecture", "refuse", "retire"])
def test_une_entree_qui_n_est_plus_publique_quitte_le_plan(client, site_public, statut):
    rendre_public(site_public.lune, statut=statut)
    adresses = adresses_du_plan(client)
    assert "http://testserver" + LUNE not in adresses
    assert "http://testserver/fr/niveau/a2/" not in adresses


def test_un_piege_relu_d_une_entree_non_relue_ne_compte_pas(
    client, site_public, proprietaire
):
    piege = creer_piege(site_public.secrete, proprietaire, type_piege="calque")
    rendre_public(piege)
    assert "http://testserver/fr/type/calque/" not in adresses_du_plan(client)


# --- security.txt -------------------------------------------------------------


def test_security_txt_mene_au_signalement_prive(client, db):
    """Critère du PRD : security.txt mène au signalement privé de GitHub."""
    reponse = client.get("/.well-known/security.txt")
    assert reponse.status_code == 200
    assert reponse["Content-Type"] == "text/plain; charset=utf-8"
    champs = dict(
        ligne.split(": ", 1)
        for ligne in reponse.content.decode().splitlines()
        if ligne and not ligne.startswith("#")
    )
    assert champs["Contact"] == (
        "https://github.com/ColinLubout/motsencommun/security/advisories/new"
    )
    assert champs["Canonical"] == "http://testserver/.well-known/security.txt"
    assert champs["Preferred-Languages"] == "fr, en"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT00:00:00Z", champs["Expires"])


def test_security_txt_expire_dans_moins_d_un_an(client, db):
    """RFC 9116 : la date d'expiration est dans le futur, à moins d'un an."""

    texte = client.get("/.well-known/security.txt").content.decode()
    expiration = datetime.datetime.strptime(
        re.search(r"Expires: (\S+)", texte).group(1), "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=datetime.UTC)
    maintenant = datetime.datetime.now(datetime.UTC)
    assert maintenant < expiration < maintenant + datetime.timedelta(days=365)


def test_security_md_mene_au_meme_endroit():

    texte = Path(settings.BASE_DIR, "SECURITY.md").read_text("utf-8")
    assert f"{settings.DEPOT_DU_CODE}/security/advisories/new" in texte

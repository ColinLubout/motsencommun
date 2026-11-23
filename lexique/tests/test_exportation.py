"""Téléchargements : « exporter », ses fichiers, ses instantanés et la page qui y mène."""

import csv
import datetime
import io
import json
import re

import pytest
from django.conf import settings
from django.core.management import call_command

from lexique import exportation
from lexique import models as m
from lexique import vocabulaire as v
from lexique.tests.conftest import (
    SENS_POLONAIS,
    SENS_UKRAINIEN,
    creer_compte,
    creer_entree,
    creer_exemple,
    creer_piege,
    modifier,
    relire,
    rendre_public,
)

TOUS_LES_FICHIERS = [
    "mots-en-commun.json",
    "entrees.csv",
    "pieges.csv",
    "exemples.csv",
    "traductions.csv",
    "dictionnaire-de-donnees.md",
    "dictionnaire-de-donnees.en.md",
]


def dossier():
    return settings.DOSSIER_TELECHARGEMENTS


def exporter(*options):
    sortie = io.StringIO()
    call_command("exporter", *options, stdout=sortie)
    return sortie.getvalue()


def lire_json():
    return json.loads((dossier() / "mots-en-commun.json").read_text("utf-8"))


def lire_csv(nom):
    octets = (dossier() / nom).read_bytes()
    assert octets.startswith(b"\xef\xbb\xbf"), "BOM UTF-8, pour les tableurs"
    return list(csv.DictReader(io.StringIO(octets.decode("utf-8-sig"))))


def tout_le_texte():
    return "\n".join(
        (dossier() / nom).read_bytes().decode("utf-8-sig") for nom in TOUS_LES_FICHIERS
    )


def par_slug(donnees):
    return {entree["slug"]: entree for entree in donnees["entrees"]}


def textes_du_json(valeur):
    """Chaque texte contenu dans le JSON (les valeurs, pas les noms des champs)."""
    if isinstance(valeur, dict):
        for element in valeur.values():
            yield from textes_du_json(element)
    elif isinstance(valeur, list):
        for element in valeur:
            yield from textes_du_json(element)
    elif isinstance(valeur, str):
        yield valeur


# --- Les fichiers -------------------------------------------------------------


def test_exporter_ecrit_tous_les_fichiers(site_public):
    """Critère du PRD : « exporter » écrit tous les fichiers à télécharger."""
    sortie = exporter()
    assert sorted(f.name for f in dossier().iterdir()) == sorted(TOUS_LES_FICHIERS)
    assert "2 entrée(s) exportée(s)" in sortie


def test_au_lancement_les_fichiers_sont_vides(db):
    """PRD : le site en ligne part d'une base vide ; les fichiers n'ont que leurs en-têtes."""
    exporter()
    assert lire_json()["entrees"] == []
    for nom in exportation.FICHIERS_CSV:
        assert lire_csv(nom) == []
        entetes = (dossier() / nom).read_text("utf-8-sig").splitlines()[0]
        assert entetes == ",".join(exportation.COLONNES[nom])


def test_aucun_fichier_a_moitie_ecrit_ne_reste(site_public):
    exporter()
    exporter()
    assert not [f for f in dossier().rglob("*") if "provisoire" in f.name]


# --- Ce qui sort, et ce qui ne sort pas ---------------------------------------


def test_seul_le_contenu_relu_est_exporte(site_public):
    """Critère du PRD : les téléchargements ne contiennent que du contenu relu."""
    exporter()
    entrees = par_slug(lire_json())
    assert list(entrees) == ["etre-dans-la-lune", "poser-un-lapin"]
    lapin = entrees["poser-un-lapin"]
    assert [p["type_piege"] for p in lapin["pieges"]] == ["sens_figure"]
    assert [x["phrase"] for x in lapin["exemples"]] == [
        "Il m'a posé un lapin hier soir."
    ]
    assert lapin["liens"] == [{"type_lien": "voir_aussi", "cible": "etre-dans-la-lune"}]
    texte = tout_le_texte()
    for cache in ("expression secrète", "expression-secrete", "pas encore relue"):
        assert cache not in texte, cache


@pytest.mark.parametrize("statut", ["brouillon", "en_relecture", "refuse"])
def test_ni_brouillon_ni_relecture_ni_refus(site_public, statut):
    rendre_public(site_public.lune, statut=statut)
    rendre_public(site_public.traduction, statut=statut)
    exporter()
    entrees = par_slug(lire_json())
    assert list(entrees) == ["poser-un-lapin"]
    assert entrees["poser-un-lapin"]["liens"] == []
    assert entrees["poser-un-lapin"]["traductions"] == {}
    assert "to stand someone up" not in tout_le_texte()


def test_valide_sort_aussi(site_public):
    rendre_public(site_public.secrete, statut="valide")
    exporter()
    assert par_slug(lire_json())["expression-secrete"]["statut"] == "valide"


@pytest.fixture
def publiee_puis_retiree(db, proprietaire, relecteur):
    """Une entrée relue (vraie relecture), puis retirée par le propriétaire, texte modifié."""
    entree = creer_entree(proprietaire, slug="retiree", vedette="une entrée retirée")
    relire(entree, relecteur)
    entree.refresh_from_db()
    modifier(entree, proprietaire, statut="retire", sens_b1="Un texte jamais relu.")
    return entree


def test_un_contenu_retire_apres_publication_reste_marque_retire(publiee_puis_retiree):
    """PRD : un slug ne disparaît pas ; l'entrée retirée reste, marquée « retire »."""
    exporter()
    retiree = par_slug(lire_json())["retiree"]
    assert retiree["statut"] == "retire"
    # Sa dernière version publiée, jamais le texte qui n'a pas été relu.
    assert retiree["sens_b1"] == "Ne pas venir à un rendez-vous, sans prévenir."
    assert "Un texte jamais relu." not in tout_le_texte()


def test_un_contenu_retire_sans_avoir_ete_publie_ne_sort_pas(db, proprietaire):
    entree = creer_entree(proprietaire, slug="jamais-publiee", vedette="jamais publiée")
    modifier(entree, proprietaire, statut="retire")
    exporter()
    assert lire_json()["entrees"] == []


def test_un_lien_vers_une_entree_retiree_reste(site_public, publiee_puis_retiree):
    m.LienEntree.objects.create(
        entree=site_public.lapin, cible=publiee_puis_retiree, type_lien="contraire"
    )
    exporter()
    liens = par_slug(lire_json())["poser-un-lapin"]["liens"]
    assert {"type_lien": "contraire", "cible": "retiree"} in liens


# --- Crédits et vie privée ----------------------------------------------------


@pytest.fixture
def relu_pour_de_vrai(db, proprietaire, relecteur, tuteur):
    """Une entrée, son piège, son exemple et sa traduction, approuvés par de vraies relectures."""
    for compte, nom in (
        (proprietaire, "Colin"),
        (relecteur, "Тарас"),
        (tuteur, "Agnieszka"),
    ):
        compte.contributeur.nom_affiche = nom
        compte.contributeur.save()
    entree = creer_entree(proprietaire)
    piege = creer_piege(entree, proprietaire)
    exemple = creer_exemple(entree, proprietaire)
    traduction = m.EntreeTraduction.objects.create(
        entree=entree, langue="en", sens="to stand someone up", ajoute_par=proprietaire
    )
    for contenu in (entree, piege, exemple):
        relire(contenu, relecteur)
    relire(traduction, tuteur)
    return entree


def test_chaque_enregistrement_porte_ses_credits(relu_pour_de_vrai):
    exporter()
    donnees = lire_json()
    lapin = donnees["entrees"][0]
    assert lapin["ajoute_par"] == "Colin"
    assert lapin["relecteurs"] == ["Тарас"]
    assert lapin["pieges"][0]["relecteurs"] == ["Тарас"]
    assert lapin["exemples"][0]["relecteurs"] == ["Тарас"]
    assert lapin["traductions"]["en"]["relecteurs"] == ["Agnieszka"]
    assert donnees["contributeurs"] == ["Agnieszka", "Colin", "Тарас"]
    assert lire_csv("entrees.csv")[0]["relecteurs"] == "Тарас"


def test_ni_adresse_ni_compte_ne_sortent(relu_pour_de_vrai):
    """Critère du PRD : les noms affichés, jamais les adresses e-mail."""
    exporter()
    valeurs = list(textes_du_json(lire_json()))
    for nom in exportation.FICHIERS_CSV:
        valeurs += [cellule for ligne in lire_csv(nom) for cellule in ligne.values()]
    assert "Тарас" in valeurs
    for valeur in valeurs:
        assert "@" not in valeur, valeur
        for compte in ("proprietaire", "relecteur", "tuteur"):
            assert compte not in valeur, valeur


# --- Forme des fichiers -------------------------------------------------------


def test_le_json_suit_l_exemple_du_prd(site_public):
    exporter()
    donnees = lire_json()
    assert donnees["titre"] == "Mots en commun"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", donnees["exporte_le"])
    assert donnees["licence"]["nom"] == "CC BY 4.0"
    assert donnees["licence"]["credit"] == "Contributeurs de Mots en commun"
    assert donnees["dictionnaire_de_donnees"] == "dictionnaire-de-donnees.md"
    assert donnees["contributeurs"] == ["proprietaire"]
    assert donnees["themes"] == [
        {"slug": "relations", "nom": "Relations", "traductions": {}},
        {"slug": "temps", "nom": "Temps et durée", "traductions": {}},
    ]
    lapin = par_slug(donnees)["poser-un-lapin"]
    attendu = {
        "slug": "poser-un-lapin",
        "vedette": "poser un lapin à qqn",
        "type_entree": "expression",
        "nature": "locution_verbale",
        "niveau": "B1",
        "registre": "familier",
        "sens_b1": "Ne pas venir à un rendez-vous, sans prévenir.",
        "sens_a2": None,
        "statut": "relu",
        "ajoute_par": "proprietaire",
        "themes": ["relations"],
    }
    assert {cle: lapin[cle] for cle in attendu} == attendu
    piege = lapin["pieges"][0]
    assert piege["type_piege"] == "sens_figure"
    assert piege["gravite"] == "moyenne"
    assert piege["concerne"] == ["comprehension"]
    assert piege["langue_apprenant"] is None
    assert piege["statut"] == "relu"
    exemple = lapin["exemples"][0]
    assert exemple["surlignage"] == "m'a posé un lapin"
    assert exemple["niveau"] == "B1"
    traduction = lapin["traductions"]["en"]
    assert traduction["sens"] == "to stand someone up"
    assert traduction["statut"] == "relu"


def test_les_csv_disent_la_meme_chose_que_le_json(site_public, proprietaire):
    deuxieme = creer_entree(proprietaire, slug="autre", vedette="une autre entrée")
    rendre_public(deuxieme)
    m.ExempleEntree.objects.create(
        exemple=site_public.exemple, entree=deuxieme, surlignage="lapin"
    )
    site_public.lapin.formes = ["poser un lapin", "il m'a posé un lapin"]
    m.Entree.objects.filter(pk=site_public.lapin.pk).update(
        formes=site_public.lapin.formes
    )
    exporter()
    donnees = par_slug(lire_json())
    entrees = {ligne["slug"]: ligne for ligne in lire_csv("entrees.csv")}
    assert list(entrees) == list(donnees)
    lapin = entrees["poser-un-lapin"]
    assert lapin["formes"] == "poser un lapin | il m'a posé un lapin"
    assert lapin["voir_aussi"] == "etre-dans-la-lune"
    assert lapin["sens_a2"] == ""
    assert [p["entree"] for p in lire_csv("pieges.csv")] == ["poser-un-lapin"]
    # Une phrase qui illustre deux entrées : deux lignes, même id.
    exemples = lire_csv("exemples.csv")
    assert sorted(x["entree"] for x in exemples) == ["autre", "poser-un-lapin"]
    assert len({x["id"] for x in exemples}) == 1
    assert lire_csv("traductions.csv") == [
        {
            "objet": "entree",
            "cle": "poser-un-lapin",
            "langue": "en",
            "champ": "sens",
            "texte": "to stand someone up",
            "statut": "relu",
            "ajoute_par": "proprietaire",
            "relecteurs": "",
            "cree_le": donnees["poser-un-lapin"]["traductions"]["en"]["cree_le"],
            "modifie_le": donnees["poser-un-lapin"]["traductions"]["en"]["modifie_le"],
        }
    ]


def test_les_csv_gardent_le_cyrillique_et_le_polonais(entree_multilingue, proprietaire):
    """Critère du PRD : le CSV s'ouvre dans un tableur avec les lettres ukrainiennes et polonaises."""
    rendre_public(entree_multilingue, *entree_multilingue.traductions.all())
    theme = m.Theme.objects.create(slug="relations", nom="Relations")
    entree_multilingue.themes.add(theme)
    m.ThemeTraduction.objects.create(theme=theme, langue="uk", nom="Стосунки")
    exporter()
    textes = {
        (t["objet"], t["langue"]): t["texte"] for t in lire_csv("traductions.csv")
    }
    assert textes[("entree", "uk")] == SENS_UKRAINIEN
    assert textes[("entree", "pl")] == SENS_POLONAIS
    assert textes[("theme", "uk")] == "Стосунки"
    assert "й" in SENS_UKRAINIEN and "ł" in SENS_POLONAIS
    # Le JSON aussi, sans échappement \u.
    brut = (dossier() / "mots-en-commun.json").read_text("utf-8")
    assert SENS_UKRAINIEN in brut and SENS_POLONAIS in brut


# --- Instantanés mensuels -----------------------------------------------------


@pytest.fixture
def a_la_date(monkeypatch):
    def regler(annee, mois, jour, heure=3, minute=30):
        moment = datetime.datetime(
            annee, mois, jour, heure, minute, tzinfo=datetime.UTC
        )
        monkeypatch.setattr("django.utils.timezone.now", lambda: moment)

    return regler


def instantane(mois):
    return dossier() / "instantanes" / mois


def test_le_premier_du_mois_un_instantane_est_garde(site_public, a_la_date):
    """Critère du PRD : un instantané daté est gardé le premier de chaque mois."""
    a_la_date(2026, 12, 1)
    sortie = exporter()
    assert sorted(f.name for f in instantane("2026-12").iterdir()) == sorted(
        [
            "mots-en-commun-2026-12.json",
            "entrees-2026-12.csv",
            "pieges-2026-12.csv",
            "exemples-2026-12.csv",
            "traductions-2026-12.csv",
            "dictionnaire-de-donnees-2026-12.md",
            "dictionnaire-de-donnees-2026-12.en.md",
        ]
    )
    assert "instantanes/2026-12/" in sortie
    assert (instantane("2026-12") / "mots-en-commun-2026-12.json").read_bytes() == (
        dossier() / "mots-en-commun.json"
    ).read_bytes()


def test_les_autres_jours_pas_d_instantane(site_public, a_la_date):
    a_la_date(2026, 12, 2)
    exporter()
    assert not (dossier() / "instantanes").exists()


def test_le_premier_du_mois_se_compte_a_l_heure_de_paris(site_public, a_la_date):
    a_la_date(2026, 11, 30, heure=23, minute=30)  # 0 h 30 le 1er décembre à Paris
    exporter()
    assert instantane("2026-12").is_dir()


def test_un_instantane_est_garde_pour_toujours(site_public, a_la_date):
    """Un instantané n'est jamais remplacé, même si « exporter » repasse le même mois."""
    a_la_date(2026, 12, 1)
    exporter()
    garde = instantane("2026-12") / "mots-en-commun-2026-12.json"
    avant = garde.read_bytes()
    rendre_public(site_public.secrete)
    sortie = exporter("--instantane")
    assert garde.read_bytes() == avant
    assert "existe déjà" in sortie
    # Les fichiers du jour, eux, ont bien changé.
    assert "expression-secrete" in par_slug(lire_json())


def test_l_instantane_sur_demande(site_public, a_la_date):
    a_la_date(2026, 12, 15)
    exporter("--instantane")
    assert instantane("2026-12").is_dir()


# --- La page de téléchargement ------------------------------------------------


def test_avant_le_premier_export_la_page_le_dit(client, db):
    contenu = client.get("/fr/telecharger/").content.decode()
    assert "Les fichiers ne sont pas encore disponibles." in contenu
    assert "/telechargements/" not in contenu


def test_la_page_de_telechargement_mene_aux_fichiers(client, site_public):
    """Critère du PRD : /fr/telecharger/ mène à tous les fichiers."""
    exporter()
    contenu = client.get("/fr/telecharger/").content.decode()
    for nom in TOUS_LES_FICHIERS[:-1]:
        assert f'href="/telechargements/{nom}"' in contenu, nom
    assert "dictionnaire-de-donnees.en.md" not in contenu
    assert "Les fichiers ne sont pas encore disponibles." not in contenu
    assert re.search(
        r'<span class="taille">\([\d,]+(?:\xa0|&nbsp;)?(?:octets|Ko)\)</span>', contenu
    )


def test_en_anglais_le_dictionnaire_est_en_anglais(client, site_public):
    exporter()
    contenu = client.get("/en/telecharger/").content.decode()
    assert (
        'href="/telechargements/dictionnaire-de-donnees.en.md" hreflang="en"' in contenu
    )
    assert "mots-en-commun.json" in contenu


def test_la_page_liste_les_instantanes(client, site_public, a_la_date):
    a_la_date(2026, 11, 1)
    exporter()
    a_la_date(2026, 12, 1)
    exporter()
    contenu = client.get("/fr/telecharger/").content.decode()
    assert contenu.index("Décembre 2026") < contenu.index("Novembre 2026")
    assert (
        'href="/telechargements/instantanes/2026-12/mots-en-commun-2026-12.json"'
        in contenu
    )
    assert 'href="/telechargements/instantanes/2026-11/entrees-2026-11.csv"' in contenu


def test_un_dossier_etranger_n_est_pas_un_instantane(client, site_public):
    exporter()
    (dossier() / "instantanes" / "pas-un-mois").mkdir(parents=True)
    contenu = client.get("/fr/telecharger/").content.decode()
    assert "pas-un-mois" not in contenu


# --- Le dictionnaire de données -----------------------------------------------


def noms_documentes(texte):
    """Les noms de la première colonne des tableaux « Champ » (plages « a1 … c2 » dépliées)."""
    noms = set()
    for cellule in re.findall(r"^\| `([^`|]+)` \|", texte, flags=re.MULTILINE):
        for nom in cellule.split(", "):
            plage = re.fullmatch(r"(\w+)_a1 … \1_c2", nom)
            if plage:
                noms.update(f"{plage.group(1)}_{n.lower()}" for n in v.NIVEAUX)
            else:
                noms.add(nom)
    return noms


def cles(objet, *, sauf=()):
    return set(objet) - set(sauf)


def test_le_dictionnaire_decrit_chaque_champ(site_public, proprietaire):
    m.LienEntree.objects.create(
        entree=site_public.lapin, cible=site_public.lune, type_lien="contraire"
    )
    exporter()
    donnees = lire_json()
    documentes = noms_documentes(
        (dossier() / "dictionnaire-de-donnees.md").read_text("utf-8")
    )
    lapin = par_slug(donnees)["poser-un-lapin"]
    a_documenter = (
        cles(donnees)
        | cles(lapin)
        | cles(lapin["pieges"][0])
        | cles(lapin["exemples"][0])
        | cles(lapin["traductions"]["en"])
        | {
            colonne
            for colonnes in exportation.COLONNES.values()
            for colonne in colonnes
        }
    )
    assert a_documenter - documentes == set()


def test_le_dictionnaire_donne_chaque_code(db):
    exporter()
    texte = (dossier() / "dictionnaire-de-donnees.md").read_text("utf-8")
    for _nom, vocabulaire in exportation.dictionnaire.VOCABULAIRES:
        for code, libelle in vocabulaire.choices:
            assert f"| `{code}` | {libelle} |" in texte, code
    assert "| `faux_ami` | Faux ami |" in texte


def test_le_dictionnaire_existe_en_anglais(db):
    exporter()
    francais = (dossier() / "dictionnaire-de-donnees.md").read_text("utf-8")
    anglais = (dossier() / "dictionnaire-de-donnees.en.md").read_text("utf-8")
    assert francais.startswith("# Dictionnaire de données de Mots en commun")
    assert anglais.startswith("# Mots en commun data dictionary")
    assert "| `faux_ami` | False friend |" in anglais
    # Les mêmes champs, dans les deux langues.
    assert noms_documentes(anglais) == noms_documentes(francais)


def test_les_comptes_de_test_ne_sont_pas_credites_sans_contenu(db):
    creer_compte("personne")
    exporter()
    assert lire_json()["contributeurs"] == []

"""Toutes les écritures : NFC, champ de recherche, accents du français seulement, tri par langue."""

import importlib
import io
import unicodedata

import pytest
from django.apps import apps as applications
from django.core.management import call_command
from django.urls import reverse

from lexique import models as m
from lexique import recherche as r
from lexique import vocabulaire as v
from lexique.tests.conftest import (
    creer_entree,
    creer_exemple,
    creer_piege,
    relire,
)


def nfd(texte):
    return unicodedata.normalize("NFD", texte)


def est_nfc(texte):
    return unicodedata.is_normalized("NFC", texte)


# --- NFC ----------------------------------------------------------------------


def test_chaque_texte_est_enregistre_en_nfc(db, proprietaire):
    entree = creer_entree(
        proprietaire,
        vedette=nfd("être en train de"),
        formes=[nfd("été"), "cœur"],
        sens_b1=nfd("Être occupé à faire quelque chose."),
    )
    piege = creer_piege(entree, proprietaire, explication_b1=nfd("Ça n'a rien à voir."))
    exemple = creer_exemple(
        entree,
        proprietaire,
        phrase=nfd("Il était en train de dîner."),
        surlignage=nfd("était en train de"),
    )
    traduction = m.EntreeTraduction.objects.create(
        entree=entree, langue="uk", sens=nfd("Мій край"), ajoute_par=proprietaire
    )
    theme = m.Theme.objects.create(slug="sante", nom=nfd("Santé"))
    proprietaire.contributeur.nom_affiche = nfd("Zoë Łukasiewicz")
    proprietaire.contributeur.save()

    textes = [
        *m.Entree.objects.values_list("vedette", "sens_b1").get(),
        *m.Entree.objects.get().formes,
        m.Piege.objects.values_list("explication_b1", flat=True).get(pk=piege.pk),
        m.Exemple.objects.values_list("phrase", flat=True).get(pk=exemple.pk),
        m.ExempleEntree.objects.values_list("surlignage", flat=True).get(),
        m.EntreeTraduction.objects.values_list("sens", flat=True).get(pk=traduction.pk),
        m.Theme.objects.values_list("nom", flat=True).get(pk=theme.pk),
        m.Contributeur.objects.values_list("nom_affiche", flat=True).get(
            utilisateur=proprietaire
        ),
    ]
    assert all(est_nfc(texte) for texte in textes)
    assert "й" in m.EntreeTraduction.objects.get().sens, "й reste une seule lettre"


def test_la_validation_normalise_avant_de_verifier(db, proprietaire):
    entree = creer_entree(proprietaire)
    exemple = m.Exemple(
        phrase=nfd("Il a été poli."), niveau="A2", ajoute_par=proprietaire
    )
    exemple.full_clean()
    assert est_nfc(exemple.phrase)
    exemple.save()
    lien = m.ExempleEntree(exemple=exemple, entree=entree, surlignage=nfd("a été"))
    lien.full_clean()
    assert lien.surlignage == "a été"


@pytest.mark.parametrize("quoi", ["entrée", "piège"])
def test_un_texte_identique_sous_une_autre_forme_n_est_pas_une_modification(
    db, proprietaire, relecteur, quoi
):
    """Un contenu relu ne repart pas en relecture pour un simple changement de forme Unicode."""
    entree = creer_entree(proprietaire, vedette="être en train de")
    if quoi == "entrée":
        contenu, champ = entree, "vedette"
    else:
        # Piege n'a pas son propre save() : seul Contenu.save() normalise.
        contenu = creer_piege(
            entree, proprietaire, explication_b1="Ça n'a rien à voir."
        )
        champ = "explication_b1"
    relire(contenu, relecteur)
    contenu.refresh_from_db()
    assert contenu.statut == v.Statut.RELU
    avant = contenu.texte_modifie_le

    setattr(contenu, champ, nfd(getattr(contenu, champ)))
    contenu.save()

    contenu.refresh_from_db()
    assert contenu.statut == v.Statut.RELU
    assert contenu.texte_modifie_le == avant


# --- Apostrophes --------------------------------------------------------------


def test_apostrophes_droites_dans_les_formes_les_phrases_et_les_surlignages(
    db, proprietaire
):
    entree = creer_entree(
        proprietaire,
        vedette="en avoir marre",
        formes=["j’en ai marre", "t’en as marre"],
        sens_b1="Ne plus supporter quelque chose : on n’en peut plus.",
    )
    exemple = creer_exemple(
        entree,
        proprietaire,
        phrase="J’en ai marre de la pluie.",
        surlignage="J’en ai marre",
    )
    entree.refresh_from_db()
    exemple.refresh_from_db()
    assert entree.formes == ["j'en ai marre", "t'en as marre"]
    assert exemple.phrase == "J'en ai marre de la pluie."
    assert exemple.liens_entrees.get().surlignage == "J'en ai marre"
    assert "n’en peut" in entree.sens_b1, "les autres textes gardent leur apostrophe"


def test_un_surlignage_et_sa_phrase_tapes_avec_des_apostrophes_differentes(
    db, proprietaire
):
    entree = creer_entree(proprietaire)
    exemple = creer_exemple(
        entree,
        proprietaire,
        phrase="Il m'a posé un lapin.",
        surlignage="m’a posé un lapin",
    )
    assert exemple.liens_entrees.get().surlignage == "m'a posé un lapin"

    # Dans un formulaire, la phrase n'est pas encore normalisée.
    lien = m.ExempleEntree(
        exemple=m.Exemple(phrase="Elle m’a posé un lapin.", niveau="B1"),
        entree=entree,
        surlignage="m'a posé un lapin",
    )
    lien.clean()


# --- Champs de recherche ------------------------------------------------------


def test_le_champ_de_recherche_d_une_entree(db, proprietaire):
    entree = creer_entree(
        proprietaire,
        vedette="Être en train de",
        precision="durée",
        formes=["être en train de", "en train de"],
        sens_a2="Faire quelque chose maintenant.",
        sens_b1="",
        sens_c1="Action en cours.",
        sens_litteral="Sur le train",
    )
    assert entree.recherche.split("\n") == [
        "etre en train de",
        "etre en train de",
        "en train de",
        "faire quelque chose maintenant.",
        "action en cours.",
    ]


def test_le_champ_de_recherche_d_une_traduction_garde_ses_signes(entree_multilingue):
    ukrainienne = entree_multilingue.traductions.get(langue="uk")
    polonaise = entree_multilingue.traductions.get(langue="pl")
    assert ukrainienne.recherche == "мій рідний край — київ. без м'яса й хліба."
    assert polonaise.recherche == "łódź to miasto, a łąka jest zielona."


# --- Chercher -----------------------------------------------------------------


def resultats(requete, langue="fr", **restrictions):
    return [str(entree) for entree in r.chercher(requete, langue, **restrictions)]


def test_etre_en_train_trouve_etre_en_train_de(db, proprietaire):
    """Critère du PRD : la recherche ignore accents et majuscules en français."""
    creer_entree(
        proprietaire, vedette="Être en train de", sens_b1="Faire en ce moment."
    )
    creer_entree(proprietaire, vedette="poser un lapin à qqn")
    for requete in ("etre en train", "ETRE EN TRAIN", "être en train", "Etre En Train"):
        assert resultats(requete) == ["Être en train de"]


def test_le_cyrillique_ignore_la_casse_sans_confondre_les_lettres(entree_multilingue):
    """Critère du PRD : Київ / київ, mais jamais й pour и."""
    vedette = str(entree_multilingue)
    for requete in ("київ", "КИЇВ", "Київ", "край", "КРАЙ", "м'яса", "мʼяса", "м’яса"):
        assert resultats(requete, "uk") == [vedette], requete
    for requete in ("краи", "киів", "киев", "мясо"):
        assert resultats(requete, "uk") == [], requete


def test_le_polonais_garde_ses_lettres(entree_multilingue):
    """Critère du PRD : le ł polonais est préservé."""
    vedette = str(entree_multilingue)
    for requete in ("łódź", "ŁÓDŹ", "Łąka"):
        assert resultats(requete, "pl") == [vedette], requete
    for requete in ("lodz", "łodz", "laka"):
        assert resultats(requete, "pl") == [], requete


def test_les_traductions_ne_comptent_que_dans_leur_langue(entree_multilingue):
    assert resultats("київ", "pl") == []
    assert resultats("łódź", "uk") == []
    assert resultats("київ", "fr") == []


def test_tous_les_mots_dans_n_importe_quel_ordre(db, proprietaire):
    creer_entree(proprietaire, vedette="poser un lapin à qqn")
    creer_entree(proprietaire, vedette="être dans la lune", sens_b1="Rêver.")
    assert resultats("lapin poser") == ["poser un lapin à qqn"]
    assert resultats("poser lune") == []


def test_les_correspondances_exactes_d_abord(db, proprietaire):
    creer_entree(proprietaire, vedette="tout à fait", sens_b1="Oui, en fait.")
    creer_entree(proprietaire, vedette="il en fait trop", sens_b1="Il exagère.")
    creer_entree(proprietaire, vedette="en effet", sens_b1="C'est vrai.")
    creer_entree(proprietaire, vedette="en fait", sens_b1="En réalité.")
    creer_entree(
        proprietaire,
        vedette="du coup",
        formes=["du coup", "En fait"],
        sens_b1="Donc, en fait.",
    )
    assert resultats("en fait") == [
        "du coup",  # une forme identique
        "en fait",  # la vedette identique
        "il en fait trop",  # une vedette qui contient la requête
        "tout à fait",  # seulement dans le sens
    ]


def test_une_requete_vide_ne_trouve_rien(db, proprietaire):
    creer_entree(proprietaire)
    assert resultats("") == []
    assert resultats("   ") == []


def test_chercher_seulement_dans_ce_qu_on_lui_donne(entree_multilingue, proprietaire):
    autre = creer_entree(proprietaire, vedette="un lapin", sens_b1="Un animal.")
    assert resultats("lapin", entrees=m.Entree.objects.exclude(pk=autre.pk)) == [
        str(entree_multilingue)
    ]
    assert (
        resultats(
            "київ",
            "uk",
            traductions=m.EntreeTraduction.objects.exclude(langue="uk"),
        )
        == []
    )


# --- Tri ----------------------------------------------------------------------


def test_les_entrees_se_rangent_dans_l_ordre_alphabetique_francais(db, proprietaire):
    for vedette, precision in [
        ("zèbre", ""),
        ("Être", ""),
        ("école", ""),
        ("ancienne", ""),
        ("ancien", "avant le nom"),
        ("abri", ""),
        ("ancien", "après le nom"),
    ]:
        creer_entree(proprietaire, vedette=vedette, precision=precision)
    assert [str(entree) for entree in m.Entree.objects.all()] == [
        "abri",
        "ancien (après le nom)",
        "ancien (avant le nom)",
        "ancienne",
        "école",
        "Être",
        "zèbre",
    ]


def test_la_cle_de_tri_suit_la_vedette(db, proprietaire):
    entree = creer_entree(proprietaire, vedette="zèbre")
    creer_entree(proprietaire, vedette="lapin")
    entree.vedette = "abeille"
    entree.save()
    assert [e.vedette for e in m.Entree.objects.all()] == ["abeille", "lapin"]


def test_les_noms_de_themes_traduits_se_trient_dans_leur_langue(db):
    for slug, nom in [("a", "żaba"), ("b", "łąka"), ("c", "lampa"), ("d", "zebra")]:
        theme = m.Theme.objects.create(slug=slug, nom=slug)
        m.ThemeTraduction.objects.create(theme=theme, langue="pl", nom=nom)
    traductions = m.ThemeTraduction.objects.filter(langue="pl")
    assert [t.nom for t in r.trier(traductions, "pl", cle=lambda t: t.nom)] == [
        "lampa",
        "łąka",
        "zebra",
        "żaba",
    ]


# --- Champs calculés et reconstruction ----------------------------------------


def test_les_champs_calcules_ne_sont_ni_modifiables_ni_dans_l_historique():
    for modele, champs in [
        (m.Entree, ["recherche", "cle_de_tri"]),
        (m.EntreeTraduction, ["recherche"]),
    ]:
        for nom in champs:
            assert not modele._meta.get_field(nom).editable
            assert nom not in [c.name for c in modele.history.model._meta.fields]
            assert nom in m.Contenu.CHAMPS_HORS_TEXTE


def corrompre():
    m.Entree.objects.update(recherche="", cle_de_tri=b"")
    m.EntreeTraduction.objects.update(recherche="")


def nombres_d_historique():
    return m.Entree.history.count(), m.EntreeTraduction.history.count()


def test_reconstruire_recherche(entree_multilingue, relecteur):
    relire(entree_multilingue, relecteur)
    entree_multilingue.refresh_from_db()
    attendu = (
        entree_multilingue.recherche,
        bytes(entree_multilingue.cle_de_tri),
        entree_multilingue.texte_modifie_le,
    )
    historique = nombres_d_historique()
    corrompre()

    sortie = io.StringIO()
    call_command("reconstruire_recherche", stdout=sortie)

    assert "1 entrée mise à jour, 2 traductions mises à jour" in sortie.getvalue()
    entree_multilingue.refresh_from_db()
    assert (
        entree_multilingue.recherche,
        bytes(entree_multilingue.cle_de_tri),
        entree_multilingue.texte_modifie_le,
    ) == attendu
    assert entree_multilingue.statut == v.Statut.RELU, "le statut ne bouge pas"
    assert nombres_d_historique() == historique, "l'historique ne bouge pas"
    assert resultats("київ", "uk") == [str(entree_multilingue)]

    sortie = io.StringIO()
    call_command("reconstruire_recherche", stdout=sortie)
    assert "0 entrée mise à jour, 0 traduction mise à jour" in sortie.getvalue()


def test_la_migration_remplit_les_champs_des_donnees_existantes(entree_multilingue):
    migration = importlib.import_module("lexique.migrations.0002_recherche_et_tri")
    attendu = entree_multilingue.recherche
    corrompre()
    migration.calculer_recherche_et_tri(applications, None)
    entree_multilingue.refresh_from_db()
    assert entree_multilingue.recherche == attendu
    assert all(t.recherche for t in m.EntreeTraduction.objects.all())


# --- Administration -----------------------------------------------------------


def test_la_recherche_de_l_administration_ignore_accents_et_casse(
    client_proprietaire, proprietaire
):
    creer_entree(proprietaire, vedette="Être en train de")
    creer_entree(proprietaire, vedette="poser un lapin à qqn")
    reponse = client_proprietaire.get(
        reverse("admin:lexique_entree_changelist"), {"q": "ETRE train"}
    )
    assert reponse.status_code == 200
    assert "Être en train de" in reponse.content.decode()
    assert "poser un lapin" not in reponse.content.decode()

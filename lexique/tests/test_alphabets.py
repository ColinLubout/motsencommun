"""Clés de recherche et tri par langue (lexique/recherche.py), sans base de données."""

import unicodedata

import pytest

from lexique import recherche as r
from lexique.tests.conftest import (
    FRANCAIS_DANS_L_ORDRE,
    POLONAIS_DANS_L_ORDRE,
    UKRAINIEN_DANS_L_ORDRE,
)


def nfd(texte):
    return unicodedata.normalize("NFD", texte)


# --- Clés de recherche --------------------------------------------------------


@pytest.mark.parametrize(
    ("texte", "langue", "cle"),
    [
        ("Être en train de", "fr", "etre en train de"),
        ("ÉLÈVE", "fr", "eleve"),
        ("Ça va", "fr", "ca va"),
        ("cœur", "fr", "coeur"),
        ("j’en  ai\tmarre ", "fr", "j'en ai marre"),
        (nfd("été"), "fr", "ete"),
        ("à Київ", "fr", "a київ"),
        ("Київ", "uk", "київ"),
        ("КРАЙ", "uk", "край"),
        ("Їжак", "uk", "їжак"),
        ("мʼясо", "uk", "м'ясо"),
        ("Łódź", "pl", "łódź"),
        ("ŻABA", "pl", "żaba"),
        ("Café", "en", "café"),
    ],
)
def test_cle_de_recherche(texte, langue, cle):
    assert r.cle_de_recherche(texte, langue) == cle


def test_les_mots_d_une_requete():
    assert r.mots("  Être   EN train ", "fr") == ["etre", "en", "train"]
    assert r.mots("", "fr") == []


# --- Tri ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("langue", "dans_l_ordre"),
    [
        ("pl", POLONAIS_DANS_L_ORDRE),
        ("uk", UKRAINIEN_DANS_L_ORDRE),
        ("fr", FRANCAIS_DANS_L_ORDRE),
    ],
)
def test_le_tri_suit_l_alphabet_de_chaque_langue(langue, dans_l_ordre):
    melange = dans_l_ordre[::-1][::2] + dans_l_ordre[::-1][1::2]
    assert melange != dans_l_ordre
    assert r.trier(melange, langue) == dans_l_ordre


def test_en_polonais_l_barre_vient_apres_l_et_pas_apres_z():
    assert r.trier(["zebra", "łąka", "lampa", "mama"], "pl") == [
        "lampa",
        "łąka",
        "mama",
        "zebra",
    ]


def test_une_vedette_se_range_avant_ses_prolongements_quelle_que_soit_sa_precision():
    """La clé d'une vedette suivie de sa précision reste avant une vedette plus longue."""
    assert r.cle_de_tri("ancien", "zz", langue="fr") < r.cle_de_tri(
        "anciena", "", langue="fr"
    )


def test_une_langue_inconnue_d_icu_se_trie_quand_meme():
    assert r.trier(["b", "a"], "") == ["a", "b"]

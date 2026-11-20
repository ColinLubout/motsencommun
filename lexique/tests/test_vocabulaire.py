"""Les vocabulaires reprennent exactement les codes du PRD."""

import pytest

from lexique import vocabulaire as v

CODES_DU_PRD = {
    v.Niveau: ["A1", "A2", "B1", "B2", "C1", "C2"],
    v.TypeEntree: ["mot", "expression", "construction"],
    v.Nature: [
        "nom",
        "verbe",
        "adjectif",
        "adverbe",
        "preposition",
        "conjonction",
        "pronom",
        "determinant",
        "numeral",
        "interjection",
        "locution_verbale",
        "locution_nominale",
        "locution_adjectivale",
        "locution_adverbiale",
        "locution_prepositionnelle",
        "locution_conjonctive",
        "phrase",
    ],
    v.Genre: ["masculin", "feminin", "epicene", "pluriel_seulement"],
    v.Registre: [
        "soutenu",
        "courant",
        "familier",
        "tres_familier",
        "vulgaire",
        "argot",
    ],
    v.Frequence: ["tres_courante", "courante", "peu_courante", "rare"],
    v.Region: ["FR", "BE", "CH", "CA_QC", "LU", "AF"],
    v.Concerne: ["comprehension", "production"],
    v.Gravite: ["faible", "moyenne", "elevee"],
    v.TypeLien: ["voir_aussi", "contraire", "a_ne_pas_confondre", "variante"],
    v.Statut: ["brouillon", "en_relecture", "relu", "valide", "refuse", "retire"],
    v.TypePiege: [
        "sens_figure",
        "faux_ami",
        "faux_ami_partiel",
        "connotation",
        "calque",
        "construction_inversee",
        "sens_selon_position",
        "sens_selon_genre",
        "polarite",
        "prononciation",
        "mode_impose",
        "preposition",
        "forme_figee",
        "confusion_possible",
        "forme_irreguliere",
        "registre",
        "regional",
        "pragmatique",
    ],
}


@pytest.mark.parametrize("vocabulaire", CODES_DU_PRD, ids=lambda voc: voc.__name__)
def test_les_codes_sont_ceux_du_prd(vocabulaire):
    assert list(vocabulaire.values) == CODES_DU_PRD[vocabulaire]


def test_il_y_a_dix_huit_types_de_pieges():
    assert len(v.TypePiege.values) == 18


def test_les_codes_sont_en_ascii():
    for vocabulaire in [*CODES_DU_PRD, v.Decision, v.Langue]:
        for code in vocabulaire.values:
            assert code.isascii(), code


def test_les_langues_sont_des_codes_iso_639_1():
    codes = set(v.Langue.values)
    assert {"fr", "en", "pl", "uk", "es", "de", "ar", "he"} <= codes
    assert "ua" not in codes  # code de pays, pas de langue
    assert all(len(code) == 2 for code in codes)


def test_les_libelles_sont_en_francais():
    assert str(v.TypePiege.FAUX_AMI.label) == "Faux ami"
    assert str(v.Statut.VALIDE.label) == "Validé"
    assert str(v.Region.CA_QC.label) == "Québec"

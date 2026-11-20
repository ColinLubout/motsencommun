"""Les modèles, tables et champs portent les noms français du PRD."""

import pytest

from lexique import models as m

COMMUNS = {"cree_le", "modifie_le", "ajoute_par", "statut"}
NIVEAUX = ["a1", "a2", "b1", "b2", "c1", "c2"]

CHAMPS_DU_PRD = {
    m.Entree: {
        "slug",
        "vedette",
        "precision",
        "type_entree",
        "nature",
        "genre",
        "api",
        *(f"sens_{n}" for n in NIVEAUX),
        "sens_litteral",
        "niveau",
        "registre",
        "frequence",
        "regions",
        "themes",
        "formes",
        "liens",
        *COMMUNS,
    },
    m.Piege: {
        "entree",
        "type_piege",
        "concerne",
        "gravite",
        "langue_apprenant",
        "declencheur",
        *(f"explication_{n}" for n in NIVEAUX),
        "incorrect",
        "correct",
        *COMMUNS,
    },
    m.Exemple: {"phrase", "niveau", *COMMUNS},
    m.ExempleEntree: {"exemple", "entree", "surlignage", "ordre"},
    m.Theme: {"slug", "nom"},
    m.LienEntree: {"entree", "cible", "type_lien"},
    m.EntreeTraduction: {"entree", "langue", "sens", "sens_litteral", *COMMUNS},
    m.PiegeTraduction: {"piege", "langue", "explication", *COMMUNS},
    m.ExempleTraduction: {"exemple", "langue", "traduction", *COMMUNS},
    m.ThemeTraduction: {"theme", "langue", "nom"},
    m.Contributeur: {"nom_affiche", "langues", "licence_acceptee_le", "relit_langues"},
    m.Relecture: {"relecteur", "decision", "commentaire", "date"},
}


@pytest.mark.parametrize("modele", CHAMPS_DU_PRD, ids=lambda modele: modele.__name__)
def test_les_champs_du_prd_existent(modele):
    noms = {champ.name for champ in modele._meta.get_fields()}
    assert CHAMPS_DU_PRD[modele] <= noms


@pytest.mark.parametrize("modele", CHAMPS_DU_PRD, ids=lambda modele: modele.__name__)
def test_les_tables_portent_le_nom_du_modele(modele):
    assert modele._meta.db_table == f"lexique_{modele.__name__.lower()}"


def test_les_noms_sont_en_ascii():
    for modele in CHAMPS_DU_PRD:
        assert modele.__name__.isascii()
        for champ in modele._meta.get_fields():
            assert champ.name.isascii(), f"{modele.__name__}.{champ.name}"

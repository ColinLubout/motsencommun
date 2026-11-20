"""Règles des modèles : slugs, listes de codes, traductions, liens et surlignages."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from lexique import models as m
from lexique.models import slug_depuis
from lexique.tests.conftest import creer_entree, creer_exemple

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("vedette", "precision", "slug"),
    [
        ("poser un lapin à qqn", "", "poser-un-lapin"),
        ("en vouloir à qqn", "", "en-vouloir"),
        ("avoir besoin de qqch", "", "avoir-besoin"),
        ("n'importe quoi", "", "nimporte-quoi"),
        ("ce n’est pas la mer à boire", "", "ce-nest-pas-la-mer-a-boire"),
        ("avoir le cœur sur la main", "", "avoir-le-coeur-sur-la-main"),
        ("propre", "avant le nom", "propre-avant-le-nom"),
        ("Être en train de", "", "etre-en-train-de"),
    ],
)
def test_le_slug_vient_de_la_vedette(vedette, precision, slug):
    assert slug_depuis(vedette, precision) == slug


def test_le_slug_est_cree_a_l_enregistrement(proprietaire):
    assert creer_entree(proprietaire).slug == "poser-un-lapin"


def test_le_slug_ne_change_jamais(proprietaire):
    entree = creer_entree(proprietaire)
    entree.vedette = "poser un lapin à quelqu'un"
    entree.save()
    assert entree.slug == "poser-un-lapin"
    entree.slug = "autre-chose"
    with pytest.raises(ValidationError, match="ne change jamais"):
        entree.save()


def test_deux_entrees_ne_partagent_pas_un_slug(proprietaire):
    creer_entree(proprietaire)
    with pytest.raises(ValidationError, match="déjà le slug"):
        creer_entree(proprietaire)
    creer_entree(proprietaire, precision="sens figuré")  # la précision les distingue


def test_les_regions_sont_des_codes_du_vocabulaire(proprietaire):
    entree = creer_entree(proprietaire, regions=["FR", "CA_QC"])
    entree.full_clean()
    entree.regions = ["FR", "QC"]
    with pytest.raises(ValidationError, match="QC"):
        entree.full_clean()


def test_les_formes_sont_une_liste_de_textes(proprietaire):
    entree = creer_entree(proprietaire, formes=["j'en ai marre", "t'en as marre"])
    entree.full_clean()
    entree.refresh_from_db()
    assert entree.formes == ["j'en ai marre", "t'en as marre"]


def test_un_piege_concerne_au_moins_une_competence(proprietaire):
    piege = m.Piege(
        entree=creer_entree(proprietaire),
        ajoute_par=proprietaire,
        type_piege="faux_ami",
        concerne=[],
        gravite="elevee",
    )
    with pytest.raises(ValidationError) as erreur:
        piege.full_clean()
    assert "concerne" in erreur.value.message_dict


def test_une_traduction_n_est_pas_en_francais(proprietaire):
    traduction = m.EntreeTraduction(
        entree=creer_entree(proprietaire),
        langue="fr",
        sens="…",
        ajoute_par=proprietaire,
    )
    with pytest.raises(ValidationError, match="langue d'origine"):
        traduction.full_clean()


def test_une_seule_traduction_par_langue(proprietaire):
    entree = creer_entree(proprietaire)
    m.EntreeTraduction.objects.create(
        entree=entree, langue="en", ajoute_par=proprietaire
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        m.EntreeTraduction.objects.create(
            entree=entree, langue="en", ajoute_par=proprietaire
        )


def test_une_entree_n_est_pas_liee_a_elle_meme(proprietaire):
    entree = creer_entree(proprietaire)
    lien = m.LienEntree(entree=entree, cible=entree, type_lien="voir_aussi")
    with pytest.raises(ValidationError):
        lien.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        lien.save()


def test_un_surlignage_absent_de_la_phrase_est_refuse(proprietaire):
    """Critère d'acceptation : enregistrer un surlignage absent de la phrase est refusé."""
    entree = creer_entree(proprietaire)
    exemple = m.Exemple.objects.create(
        phrase="Il m'a posé un lapin hier soir.", niveau="B1", ajoute_par=proprietaire
    )
    lien = m.ExempleEntree(
        exemple=exemple, entree=entree, surlignage="m'a posé une lapine"
    )
    message = "« m'a posé une lapine » n'apparaît pas dans la phrase"
    with pytest.raises(ValidationError, match=message):
        lien.full_clean()
    with pytest.raises(ValidationError, match=message):
        lien.save()
    assert not m.ExempleEntree.objects.exists()


def test_changer_la_phrase_doit_garder_les_surlignages(proprietaire):
    exemple = creer_exemple(creer_entree(proprietaire), proprietaire)
    exemple.phrase = "Elle est venue au rendez-vous."
    with pytest.raises(ValidationError, match="ne contient plus « m'a posé un lapin »"):
        exemple.save()


def test_une_phrase_peut_illustrer_plusieurs_entrees(proprietaire):
    lapin = creer_entree(proprietaire)
    actuellement = creer_entree(proprietaire, vedette="actuellement", type_entree="mot")
    exemple = creer_exemple(
        lapin, proprietaire, phrase="Actuellement, il m'a posé un lapin chaque semaine."
    )
    m.ExempleEntree.objects.create(
        exemple=exemple, entree=actuellement, surlignage="Actuellement"
    )
    assert m.Exemple.objects.count() == 1
    assert list(lapin.exemples.all()) == [exemple]
    assert list(actuellement.exemples.all()) == [exemple]


def test_chaque_compte_a_un_profil_de_contributeur(import_initial):
    assert import_initial.contributeur.nom_affiche == "import-initial"


def test_la_marque_ia_ne_se_modifie_pas_dans_les_formulaires(proprietaire):
    for modele in (
        m.Entree,
        m.Piege,
        m.Exemple,
        m.Theme,
        m.LienEntree,
        m.EntreeTraduction,
    ):
        champ = modele._meta.get_field("genere_par_ia")
        assert champ.editable is False
        assert champ.default is False

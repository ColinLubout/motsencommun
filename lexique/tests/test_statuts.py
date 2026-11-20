"""Le statut d'un contenu suit ses relectures, et personne ne relit son propre travail."""

import pytest
from django.core.exceptions import ValidationError

from lexique import models as m
from lexique import vocabulaire as v
from lexique.tests.conftest import (
    creer_compte,
    creer_entree,
    creer_exemple,
    creer_piege,
    modifier,
    relire,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def entree_importee(import_initial):
    """Une entrée de départ, avec un piège expliqué : prête à être relue."""
    entree = creer_entree(import_initial)
    creer_piege(entree, import_initial)
    return entree


@pytest.mark.parametrize("statut", ["relu", "valide", "refuse"])
def test_ces_statuts_ne_se_choisissent_pas(entree_importee, statut):
    entree_importee.statut = statut
    with pytest.raises(ValidationError):
        entree_importee.save()
    entree_importee.refresh_from_db()
    assert entree_importee.statut == v.Statut.BROUILLON


def test_une_approbation_donne_relu_et_deux_donnent_valide(
    entree_importee, relecteur, tuteur
):
    relire(entree_importee, relecteur)
    entree_importee.refresh_from_db()
    assert entree_importee.statut == v.Statut.RELU
    relire(entree_importee, tuteur)
    entree_importee.refresh_from_db()
    assert entree_importee.statut == v.Statut.VALIDE


def test_la_meme_personne_n_approuve_pas_deux_fois(entree_importee, relecteur):
    relire(entree_importee, relecteur)
    with pytest.raises(ValidationError, match="déjà approuvé"):
        relire(entree_importee, relecteur)


def test_personne_ne_relit_ce_qu_il_a_ajoute(proprietaire):
    """Critère d'acceptation : personne ne met son propre contenu en « relu » ou « validé »."""
    entree = creer_entree(proprietaire)
    creer_piege(entree, proprietaire)
    with pytest.raises(ValidationError, match="ajouté ou modifié"):
        relire(entree, proprietaire)
    entree.refresh_from_db()
    assert entree.statut == v.Statut.BROUILLON


def test_personne_ne_relit_ce_qu_il_a_modifie(entree_importee, proprietaire, relecteur):
    """Écrire le sens d'une entrée importée interdit ensuite de l'approuver soi-même."""
    modifier(entree_importee, proprietaire, sens_b1="Ne pas venir au rendez-vous.")
    with pytest.raises(ValidationError, match="ajouté ou modifié"):
        relire(entree_importee, proprietaire)
    relire(entree_importee, relecteur)
    entree_importee.refresh_from_db()
    assert entree_importee.statut == v.Statut.RELU


def test_approuver_ne_fait_pas_de_vous_un_editeur(
    entree_importee, relecteur, proprietaire
):
    relire(entree_importee, relecteur)
    assert relecteur.pk not in m.Entree.objects.get(pk=entree_importee.pk).editeurs()


def test_modifier_un_contenu_relu_le_renvoie_en_relecture(
    entree_importee, proprietaire, relecteur, tuteur
):
    relire(entree_importee, relecteur)
    entree = modifier(
        m.Entree.objects.get(pk=entree_importee.pk),
        proprietaire,
        sens_b1="Ne pas venir.",
    )
    assert entree.statut == v.Statut.EN_RELECTURE
    # L'approbation d'avant ne compte plus : une nouvelle donne « relu », pas « validé ».
    relire(entree, tuteur)
    entree.refresh_from_db()
    assert entree.statut == v.Statut.RELU


def test_changer_seulement_le_statut_ne_renvoie_pas_en_relecture(
    entree_importee, relecteur
):
    relire(entree_importee, relecteur)
    entree = m.Entree.objects.get(pk=entree_importee.pk)
    entree.save()
    assert entree.statut == v.Statut.RELU


def test_une_entree_sans_sens_ne_s_approuve_pas(import_initial, relecteur):
    entree = creer_entree(import_initial, sens_b1="")
    with pytest.raises(ValidationError, match="sens en français"):
        relire(entree, relecteur)


def test_les_pieges_d_une_entree_doivent_etre_expliques(import_initial, relecteur):
    entree = creer_entree(import_initial)
    piege = creer_piege(entree, import_initial, explication_b1="")
    with pytest.raises(ValidationError, match="Chaque piège"):
        relire(entree, relecteur)
    with pytest.raises(ValidationError, match="explication en français"):
        relire(piege, relecteur)


def test_un_piege_refuse_ne_bloque_pas_son_entree(import_initial, relecteur, tuteur):
    entree = creer_entree(import_initial)
    creer_piege(entree, import_initial)
    piege_douteux = creer_piege(entree, import_initial, explication_b1="")
    relire(
        piege_douteux, tuteur, decision="refuse", commentaire="Ce piège n'existe pas."
    )
    relire(entree, relecteur)
    entree.refresh_from_db()
    assert entree.statut == v.Statut.RELU


def test_un_exemple_s_approuve_s_il_illustre_une_entree(import_initial, relecteur):
    seul = m.Exemple.objects.create(
        phrase="Il pleut.", niveau="A1", ajoute_par=import_initial
    )
    with pytest.raises(ValidationError, match="au moins une entrée"):
        relire(seul, relecteur)
    exemple = creer_exemple(creer_entree(import_initial), import_initial)
    relire(exemple, relecteur)
    exemple.refresh_from_db()
    assert exemple.statut == v.Statut.RELU


def test_un_refus_demande_un_commentaire(entree_importee, relecteur):
    with pytest.raises(ValidationError, match="commentaire"):
        relire(entree_importee, relecteur, decision="refuse")
    relire(entree_importee, relecteur, decision="refuse", commentaire="Sens inexact.")
    entree_importee.refresh_from_db()
    assert entree_importee.statut == v.Statut.REFUSE


def test_chacun_relit_seulement_ses_langues(
    entree_importee, import_initial, relecteur, tuteur
):
    traduction = m.EntreeTraduction.objects.create(
        entree=entree_importee,
        langue="en",
        sens="to stand someone up",
        ajoute_par=import_initial,
    )
    with pytest.raises(ValidationError, match="« en »"):
        relire(traduction, relecteur)  # relit seulement le français
    relire(traduction, tuteur)  # relit le français et l'anglais
    traduction.refresh_from_db()
    assert traduction.statut == v.Statut.RELU


def test_une_traduction_vide_ne_s_approuve_pas(entree_importee, import_initial, tuteur):
    traduction = m.EntreeTraduction.objects.create(
        entree=entree_importee, langue="en", ajoute_par=import_initial
    )
    with pytest.raises(ValidationError, match="sens dans cette langue"):
        relire(traduction, tuteur)


def test_sans_langue_relue_on_ne_relit_rien(entree_importee):
    curieux = creer_compte("curieux", relecteur=True, relit=[])
    with pytest.raises(ValidationError, match="ne vous permet pas"):
        relire(entree_importee, curieux)


def test_un_contenu_retire_ne_se_relit_plus(entree_importee, relecteur):
    entree_importee.statut = v.Statut.RETIRE
    entree_importee.save()
    with pytest.raises(ValidationError, match="retiré"):
        relire(entree_importee, relecteur)


def test_une_relecture_ne_se_modifie_pas(entree_importee, relecteur):
    relecture = relire(entree_importee, relecteur)
    relecture.commentaire = "Après coup."
    with pytest.raises(ValidationError, match="ne se modifie pas"):
        relecture.save()

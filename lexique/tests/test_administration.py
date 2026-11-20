"""L'administration du lexique : ce que voit un relecteur, relire, éditer, et le texte échappé."""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse
from django.utils.html import escape

from lexique import models as m
from lexique import vocabulaire as v
from lexique.tests.conftest import (
    MOT_DE_PASSE,
    creer_compte,
    creer_entree,
    creer_exemple,
    creer_piege,
)

pytestmark = pytest.mark.django_db


def adresse_de_relecture(contenu):
    type_contenu = ContentType.objects.get_for_model(contenu)
    return (
        f"{reverse('admin:lexique_relecture_add')}"
        f"?type_contenu={type_contenu.pk}&id_contenu={contenu.pk}"
    )


def test_un_relecteur_entre_sans_double_authentification(client):
    """Critère d'acceptation : un relecteur ouvre l'administration sans double authentification."""
    creer_compte("relectrice", relecteur=True, relit=["fr"], mot_de_passe=MOT_DE_PASSE)
    reponse = client.post(
        reverse("admin:login"),
        {
            "username": "relectrice",
            "password": MOT_DE_PASSE,
            "next": reverse("admin:index"),
        },
    )
    assert reponse.status_code == 302
    assert client.get(reverse("admin:index")).status_code == 200


@pytest.mark.parametrize(
    "page",
    [
        "admin:auth_user_changelist",
        "admin:auth_group_changelist",
        "admin:otp_totp_totpdevice_changelist",
        "admin:otp_static_staticdevice_changelist",
        "admin:lexique_contributeur_changelist",
    ],
)
def test_un_relecteur_ne_voit_ni_comptes_ni_groupes_ni_reglages(client_relecteur, page):
    """Critère d'acceptation : un relecteur ne voit ni les comptes, ni les groupes, ni les réglages."""
    assert client_relecteur.get(reverse(page)).status_code == 403


def test_un_relecteur_voit_le_contenu_sans_pouvoir_le_modifier(
    client_relecteur, import_initial
):
    entree = creer_entree(import_initial)
    adresse = reverse("admin:lexique_entree_change", args=[entree.pk])
    assert client_relecteur.get(adresse).status_code == 200
    assert client_relecteur.post(adresse, {"vedette": "autre"}).status_code == 403
    entree.refresh_from_db()
    assert entree.vedette == "poser un lapin à qqn"


def test_un_relecteur_relit_depuis_l_administration(
    client_relecteur, import_initial, relecteur
):
    entree = creer_entree(import_initial)
    creer_piege(entree, import_initial)
    page = client_relecteur.get(
        reverse("admin:lexique_entree_change", args=[entree.pk])
    )
    assert escape(adresse_de_relecture(entree)) in page.content.decode()

    type_contenu = ContentType.objects.get_for_model(entree)
    reponse = client_relecteur.post(
        adresse_de_relecture(entree),
        {
            "type_contenu": type_contenu.pk,
            "id_contenu": entree.pk,
            "decision": "approuve",
        },
    )
    assert reponse.status_code == 302
    assert reponse.url == reverse("admin:lexique_entree_change", args=[entree.pk])
    entree.refresh_from_db()
    assert entree.statut == v.Statut.RELU
    assert entree.relectures.get().relecteur == relecteur


def test_relire_son_propre_contenu_est_refuse_dans_l_administration(
    client_proprietaire, proprietaire
):
    entree = creer_entree(proprietaire)
    creer_piege(entree, proprietaire)
    type_contenu = ContentType.objects.get_for_model(entree)
    reponse = client_proprietaire.post(
        adresse_de_relecture(entree),
        {
            "type_contenu": type_contenu.pk,
            "id_contenu": entree.pk,
            "decision": "approuve",
        },
    )
    assert reponse.status_code == 200
    assert "ajouté ou modifié" in reponse.content.decode()
    assert not m.Relecture.objects.exists()


def formulaire_d_entree(**champs):
    """Les données d'un formulaire d'entrée complet, avec ses sous-formulaires vides."""
    donnees = {
        "vedette": "en vouloir à qqn",
        "precision": "",
        "slug": "",
        "type_entree": "expression",
        "nature": "locution_verbale",
        "genre": "",
        "niveau": "B1",
        "registre": "courant",
        "frequence": "courante",
        "api": "",
        "formes": "en vouloir\nen veut",
        "sens_b1": "Être fâché contre quelqu'un.",
        "statut": "brouillon",
    }
    for prefixe in (
        "pieges",
        "liens_exemples",
        "traductions",
        "liens_sortants",
        "lexique-relecture-type_contenu-id_contenu",
    ):
        donnees |= {
            f"{prefixe}-TOTAL_FORMS": "0",
            f"{prefixe}-INITIAL_FORMS": "0",
            f"{prefixe}-MIN_NUM_FORMS": "0",
            f"{prefixe}-MAX_NUM_FORMS": "1000",
        }
    donnees.update(champs)
    return donnees


def test_le_proprietaire_ajoute_une_entree(client_proprietaire, proprietaire):
    reponse = client_proprietaire.post(
        reverse("admin:lexique_entree_add"), formulaire_d_entree()
    )
    assert reponse.status_code == 302, reponse.content.decode()[:2000]
    entree = m.Entree.objects.get()
    assert entree.slug == "en-vouloir"
    assert entree.formes == ["en vouloir", "en veut"]
    assert entree.ajoute_par == proprietaire
    assert entree.history.get().history_user == proprietaire


def test_relu_et_valide_ne_se_choisissent_pas_dans_le_formulaire(client_proprietaire):
    page = client_proprietaire.get(reverse("admin:lexique_entree_add")).content.decode()
    assert 'value="brouillon"' in page
    assert 'value="retire"' in page
    assert 'value="relu"' not in page
    assert 'value="valide"' not in page


def test_changer_une_phrase_et_son_surlignage_ensemble(
    client_proprietaire, proprietaire
):
    entree = creer_entree(proprietaire)
    exemple = creer_exemple(entree, proprietaire)
    lien = exemple.liens_entrees.get()
    donnees = {
        "phrase": "Elle m'a encore posé un lapin.",
        "niveau": "B1",
        "statut": "brouillon",
        "liens_entrees-TOTAL_FORMS": "1",
        "liens_entrees-INITIAL_FORMS": "1",
        "liens_entrees-MIN_NUM_FORMS": "0",
        "liens_entrees-MAX_NUM_FORMS": "1000",
        "liens_entrees-0-id": lien.pk,
        "liens_entrees-0-exemple": exemple.pk,
        "liens_entrees-0-entree": entree.pk,
        "liens_entrees-0-surlignage": "m'a encore posé un lapin",
        "liens_entrees-0-ordre": "0",
    }
    for prefixe in ("traductions", "lexique-relecture-type_contenu-id_contenu"):
        donnees |= {
            f"{prefixe}-TOTAL_FORMS": "0",
            f"{prefixe}-INITIAL_FORMS": "0",
            f"{prefixe}-MIN_NUM_FORMS": "0",
            f"{prefixe}-MAX_NUM_FORMS": "1000",
        }
    reponse = client_proprietaire.post(
        reverse("admin:lexique_exemple_change", args=[exemple.pk]), donnees
    )
    assert reponse.status_code == 302, reponse.content.decode()[:3000]
    exemple.refresh_from_db()
    lien.refresh_from_db()
    assert exemple.phrase == "Elle m'a encore posé un lapin."
    assert lien.surlignage == "m'a encore posé un lapin"


SCRIPT = "<script>alert(1)</script>"


def test_le_texte_des_contributeurs_est_echappe_dans_l_administration(
    client_proprietaire, import_initial
):
    """Un <script> dans chaque champ de texte reste du texte sur les pages d'administration."""
    entree = creer_entree(
        import_initial,
        vedette=SCRIPT,
        precision=SCRIPT,
        api=SCRIPT,
        sens_litteral=SCRIPT,
        formes=[SCRIPT],
        **{f"sens_{n.lower()}": SCRIPT for n in v.NIVEAUX},
    )
    piege = creer_piege(
        entree,
        import_initial,
        declencheur=SCRIPT,
        incorrect=SCRIPT,
        correct=SCRIPT,
        **{f"explication_{n.lower()}": SCRIPT for n in v.NIVEAUX},
    )
    exemple = creer_exemple(entree, import_initial, phrase=SCRIPT, surlignage=SCRIPT)
    traductions = [
        m.EntreeTraduction.objects.create(
            entree=entree,
            langue="en",
            sens=SCRIPT,
            sens_litteral=SCRIPT,
            ajoute_par=import_initial,
        ),
        m.PiegeTraduction.objects.create(
            piege=piege, langue="en", explication=SCRIPT, ajoute_par=import_initial
        ),
        m.ExempleTraduction.objects.create(
            exemple=exemple, langue="en", traduction=SCRIPT, ajoute_par=import_initial
        ),
    ]
    theme = m.Theme.objects.create(slug="essai", nom=SCRIPT)
    import_initial.contributeur.nom_affiche = SCRIPT
    import_initial.contributeur.save()

    pages = []
    for objet in [
        entree,
        piege,
        exemple,
        theme,
        import_initial.contributeur,
        *traductions,
    ]:
        nom = objet._meta.model_name
        pages += [
            reverse(f"admin:lexique_{nom}_changelist"),
            reverse(f"admin:lexique_{nom}_change", args=[objet.pk]),
            reverse(f"admin:lexique_{nom}_history", args=[objet.pk]),
        ]
    for page in pages:
        contenu = client_proprietaire.get(page).content.decode()
        assert SCRIPT not in contenu, page
        assert "&lt;script&gt;" in contenu, page


def test_un_compte_sans_droits_n_entre_pas(import_initial):
    navigateur = Client()
    navigateur.force_login(import_initial)
    reponse = navigateur.get(reverse("admin:index"))
    assert reponse.status_code == 302
    assert reverse("admin:login") in reponse.url

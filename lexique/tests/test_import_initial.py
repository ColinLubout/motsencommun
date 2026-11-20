"""Import des données initiales : correspondances du PRD, archive réelle, relance, erreurs."""

import io
import zipfile
from collections import Counter

import pytest
import yaml
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils.text import slugify

from lexique import import_initial as imp
from lexique import models as m
from lexique import vocabulaire as v
from lexique.tests.conftest import creer_entree

ARCHIVE = settings.BASE_DIR / "donnees" / "import" / "donnees-initiales.zip"

MODELES_DE_CONTENU = [
    m.Entree,
    m.Piege,
    m.Exemple,
    m.EntreeTraduction,
    m.PiegeTraduction,
    m.ExempleTraduction,
]
AUTRES_MODELES = [m.ExempleEntree, m.LienEntree, m.Theme]


def importer_par_la_commande(chemin):
    sortie = io.StringIO()
    call_command("importer_donnees_initiales", str(chemin), stdout=sortie)
    return sortie.getvalue()


def compte_d_import():
    return get_user_model().objects.get(username=imp.NOM_DU_COMPTE)


def nombres():
    """Le nombre de lignes de chaque table du lexique et de son historique."""
    modeles = MODELES_DE_CONTENU + AUTRES_MODELES
    return {
        **{modele.__name__: modele.objects.count() for modele in modeles},
        **{
            f"historique de {modele.__name__}": modele.history.count()
            for modele in modeles
        },
    }


# --- Petites archives écrites pour un test ------------------------------------


def piege(**champs):
    donnees = {
        "id": "essai.g1",
        "type": "non_compositional",
        "affects": ["comprehension"],
        "severity": "medium",
        "l1": "en",
        "note_en": "Nothing to do with rabbits: the person never came.",
    }
    donnees.update(champs)
    return donnees


def fiche(identifiant="poser-un-lapin", **champs):
    donnees = {
        "id": identifiant,
        "kind": "expression",
        "headword": "poser un lapin à qqn",
        "pos": "verb_phrase",
        "gloss_en": "to stand someone up",
        "definition_fr": "Ne pas venir à un rendez-vous, sans prévenir.",
        "cefr": "B1",
        "register": "familier",
        "frequency": "common",
        "topics": ["relationships"],
        "detect": "confident",
        "forms": ["poser un lapin"],
        "gotchas": [piege()],
        "provenance": {"method": "ai_drafted", "created": "2026-11-18"},
        "license": "CC-BY-4.0",
    }
    donnees.update(champs)
    return donnees


def phrase(identifiant, texte, *etiquettes, cefr="B1", en="An English gloss."):
    donnees = {"id": identifiant, "fr": texte, "cefr": cefr, "en": en}
    if etiquettes:
        donnees["tags"] = [{"item": item, "text": mots} for item, mots in etiquettes]
    return donnees


def ecrire_archive(dossier, fiches, phrases=()):
    """Écrit une archive dépliée (même arborescence que le zip) et renvoie sa racine."""
    racine = dossier / "donnees-initiales"
    (racine / "data" / "items").mkdir(parents=True)
    for donnees in fiches:
        (racine / "data" / "items" / f"{donnees['id']}.yaml").write_text(
            yaml.safe_dump(donnees, allow_unicode=True), encoding="utf-8"
        )
    if phrases:
        (racine / "data" / "sentences").mkdir()
        (racine / "data" / "sentences" / "0001-essai.yaml").write_text(
            yaml.safe_dump(
                {"batch": "0001-essai", "sentences": list(phrases)}, allow_unicode=True
            ),
            encoding="utf-8",
        )
    return racine


# --- Les tables de correspondance ---------------------------------------------


def vocabulaires_des_donnees():
    with zipfile.ZipFile(ARCHIVE) as archive:
        return yaml.safe_load(
            archive.read("donnees-initiales/schema/vocabularies.yaml").decode("utf-8")
        )


@pytest.mark.parametrize(
    ("vocabulaire_source", "table", "codes_valides"),
    [
        ("item_kind", imp.TYPES_ENTREE, v.TypeEntree.values),
        ("pos", imp.NATURES, v.Nature.values),
        ("gender", imp.GENRES, v.Genre.values),
        ("frequency", imp.FREQUENCES, v.Frequence.values),
        ("relation_type", imp.TYPES_LIEN, v.TypeLien.values),
        ("gotcha_type", imp.TYPES_PIEGE, v.TypePiege.values),
        ("severity", imp.GRAVITES, v.Gravite.values),
    ],
)
def test_chaque_code_des_donnees_a_sa_correspondance(
    vocabulaire_source, table, codes_valides
):
    codes_sources = set(vocabulaires_des_donnees()[vocabulaire_source])
    assert set(table) == codes_sources
    assert set(table.values()) <= set(codes_valides)


@pytest.mark.parametrize(
    ("vocabulaire_source", "codes_valides"),
    [
        ("cefr", v.Niveau.values),
        ("register", v.Registre.values),
        ("region", v.Region.values),
        ("affects", v.Concerne.values),
    ],
)
def test_les_codes_repris_tels_quels_existent_chez_nous(
    vocabulaire_source, codes_valides
):
    assert set(vocabulaires_des_donnees()[vocabulaire_source]) <= set(codes_valides)


def test_chaque_sujet_devient_un_theme_francais():
    assert set(imp.THEMES) == set(vocabulaires_des_donnees()["topic"])
    slugs = [slug for slug, _nom in imp.THEMES.values()]
    assert len(set(slugs)) == len(slugs)
    for slug, nom in imp.THEMES.values():
        assert slug == slugify(slug)
        assert nom


def test_les_18_types_de_piege_sont_tous_atteints():
    assert set(imp.TYPES_PIEGE.values()) == set(v.TypePiege.values)


@pytest.mark.parametrize(
    ("table", "source", "cible"),
    [
        ("TYPES_ENTREE", "word", "mot"),
        ("TYPES_ENTREE", "expression", "expression"),
        ("TYPES_ENTREE", "construction", "construction"),
        ("NATURES", "noun", "nom"),
        ("NATURES", "verb", "verbe"),
        ("NATURES", "verb_phrase", "locution_verbale"),
        ("NATURES", "sentence", "phrase"),
        ("GENRES", "m", "masculin"),
        ("GENRES", "f", "feminin"),
        ("GENRES", "plural_only", "pluriel_seulement"),
        ("FREQUENCES", "very_common", "tres_courante"),
        ("FREQUENCES", "common", "courante"),
        ("FREQUENCES", "uncommon", "peu_courante"),
        ("TYPES_LIEN", "contrast", "a_ne_pas_confondre"),
        ("TYPES_LIEN", "see_also", "voir_aussi"),
        ("TYPES_LIEN", "synonym", "voir_aussi"),
        ("TYPES_LIEN", "antonym", "contraire"),
        ("TYPES_LIEN", "variant", "variante"),
        ("TYPES_PIEGE", "non_compositional", "sens_figure"),
        ("TYPES_PIEGE", "false_friend", "faux_ami"),
        ("TYPES_PIEGE", "partial_false_friend", "faux_ami_partiel"),
        ("TYPES_PIEGE", "argument_structure", "construction_inversee"),
        ("TYPES_PIEGE", "meaning_by_position", "sens_selon_position"),
        ("TYPES_PIEGE", "gender_meaning", "sens_selon_genre"),
        ("TYPES_PIEGE", "polarity", "polarite"),
        ("TYPES_PIEGE", "pronunciation", "prononciation"),
        ("TYPES_PIEGE", "mood_trigger", "mode_impose"),
        ("TYPES_PIEGE", "fixed_form", "forme_figee"),
        ("TYPES_PIEGE", "confusable", "confusion_possible"),
        ("TYPES_PIEGE", "irregular_form", "forme_irreguliere"),
        ("TYPES_PIEGE", "pragmatic", "pragmatique"),
        ("TYPES_PIEGE", "register", "registre"),
        ("TYPES_PIEGE", "calque", "calque"),
        ("TYPES_PIEGE", "connotation", "connotation"),
        ("TYPES_PIEGE", "preposition", "preposition"),
        ("TYPES_PIEGE", "regional", "regional"),
        ("GRAVITES", "low", "faible"),
        ("GRAVITES", "medium", "moyenne"),
        ("GRAVITES", "high", "elevee"),
    ],
)
def test_les_correspondances_du_prd(table, source, cible):
    assert getattr(imp, table)[source] == cible


@pytest.mark.parametrize(
    ("sujet", "slug"),
    [
        ("money", "argent"),
        ("food", "nourriture"),
        ("work", "travail"),
        ("relationships", "relations"),
    ],
)
def test_les_themes_nommes_par_le_prd(sujet, slug):
    assert imp.THEMES[sujet][0] == slug


# --- Une fiche, ses pièges et ses phrases, champ par champ --------------------


def test_une_fiche_devient_une_entree_et_sa_traduction_anglaise(tmp_path, db):
    racine = ecrire_archive(
        tmp_path,
        [
            fiche(
                "ancien-avant-nom",
                kind="word",
                expression_type="idiom",
                headword="ancien",
                sense_label="before the noun",
                pos="adjective",
                gender="m",
                ipa="/ɑ̃.sjɛ̃/",
                gloss_en="former, ex-",
                definition_fr="Qui a été, mais n'est plus.",
                literal_en="old",
                transparency="semi",
                cefr="B2",
                register="courant",
                frequency="very_common",
                regions=["BE", "CH"],
                topics=["work", "time"],
                forms=["ancien", "ancienne"],
                pattern="{qqch} ancien",
            )
        ],
    )
    imp.importer(racine)

    entree = m.Entree.objects.get()
    assert entree.slug == "ancien-avant-nom"
    assert entree.vedette == "ancien"
    assert entree.precision == "avant le nom"
    assert entree.type_entree == "mot"
    assert entree.nature == "adjectif"
    assert entree.genre == "masculin"
    assert entree.api == "/ɑ̃.sjɛ̃/"
    assert entree.sens() == {"B2": "Qui a été, mais n'est plus."}
    assert entree.sens_litteral == ""
    assert entree.niveau == "B2"
    assert entree.registre == "courant"
    assert entree.frequence == "tres_courante"
    assert entree.regions == ["BE", "CH"]
    assert entree.formes == ["ancien", "ancienne"]
    assert {(t.slug, t.nom) for t in entree.themes.all()} == {
        ("travail", "Travail"),
        ("temps", "Temps et durée"),
    }

    traduction = entree.traductions.get()
    assert traduction.langue == "en"
    assert traduction.sens == "former, ex-"
    assert traduction.sens_litteral == "old"


@pytest.mark.parametrize(
    ("etiquette", "precision"),
    [
        ("after the noun", "après le nom"),
        ("carry out", "accomplir"),
        ("Québec, Belgium, Switzerland", "Québec, Belgique, Suisse"),
        ("penser à", "penser à"),
        ("X me manque", "X me manque"),
    ],
)
def test_la_precision_est_en_francais(tmp_path, db, etiquette, precision):
    imp.importer(ecrire_archive(tmp_path, [fiche(sense_label=etiquette)]))
    assert m.Entree.objects.get().precision == precision


def test_sans_genre_ni_precision_ni_api(tmp_path, db):
    imp.importer(ecrire_archive(tmp_path, [fiche()]))
    entree = m.Entree.objects.get()
    assert (entree.genre, entree.precision, entree.api, entree.regions) == (
        "",
        "",
        "",
        [],
    )
    assert entree.traductions.get().sens_litteral == ""


def test_un_piege_et_sa_traduction_anglaise(tmp_path, db):
    imp.importer(
        ecrire_archive(
            tmp_path,
            [
                fiche(
                    "actuellement",
                    gotchas=[
                        piege(
                            type="false_friend",
                            affects=["comprehension", "production"],
                            severity="high",
                            trigger="actually",
                            note_en="Actuellement means currently, not actually.",
                            wrong="Actuellement, je suis d'accord.",
                            right="En fait, je suis d'accord.",
                        )
                    ],
                )
            ],
        )
    )
    piege_importe = m.Piege.objects.get()
    assert piege_importe.entree.slug == "actuellement"
    assert piege_importe.type_piege == "faux_ami"
    assert piege_importe.concerne == ["comprehension", "production"]
    assert piege_importe.gravite == "elevee"
    assert piege_importe.langue_apprenant == "en"
    assert piege_importe.declencheur == "actually"
    assert piege_importe.incorrect == "Actuellement, je suis d'accord."
    assert piege_importe.correct == "En fait, je suis d'accord."
    assert piege_importe.explications() == {}, "l'explication en français reste vide"
    traduction = piege_importe.traductions.get()
    assert traduction.langue == "en"
    assert traduction.explication == "Actuellement means currently, not actually."


def test_la_langue_de_l_apprenant_seulement_pour_les_six_types_du_prd(tmp_path, db):
    pieges = [
        piege(id=f"essai.g{numero}", type=source)
        for numero, source in enumerate(imp.TYPES_PIEGE, start=1)
    ]
    imp.importer(ecrire_archive(tmp_path, [fiche(gotchas=pieges)]))

    langues = dict(m.Piege.objects.values_list("type_piege", "langue_apprenant"))
    assert len(langues) == 18
    assert {code for code, langue in langues.items() if langue == "en"} == {
        "faux_ami",
        "faux_ami_partiel",
        "calque",
        "connotation",
        "preposition",
        "construction_inversee",
    }
    assert set(langues.values()) == {"en", ""}


def test_les_liens_entre_entrees(tmp_path, db):
    imp.importer(
        ecrire_archive(
            tmp_path,
            [
                fiche(
                    "a",
                    related=[
                        {"type": "contrast", "target": "b"},
                        {"type": "synonym", "target": "c"},
                    ],
                ),
                fiche("b", related=[{"type": "see_also", "target": "a"}]),
                fiche("c", related=[{"type": "antonym", "target": "b"}]),
            ],
        )
    )
    liens = set(
        m.LienEntree.objects.values_list("entree__slug", "cible__slug", "type_lien")
    )
    assert liens == {
        ("a", "b", "a_ne_pas_confondre"),
        ("a", "c", "voir_aussi"),
        ("b", "a", "voir_aussi"),
        ("c", "b", "contraire"),
    }


def test_les_phrases_deviennent_des_exemples(tmp_path, db):
    imp.importer(
        ecrire_archive(
            tmp_path,
            [fiche("en-fait"), fiche("actuellement")],
            [
                phrase(
                    "s000001",
                    "Il travaille actuellement à Bruxelles.",
                    ("actuellement", "actuellement"),
                    cefr="A2",
                    en="He's currently working in Brussels.",
                ),
                phrase(
                    "s000002",
                    "En fait, il vit actuellement à Genève.",
                    ("actuellement", "actuellement"),
                    ("en-fait", "En fait"),
                ),
                phrase("s000003", "Est-ce que ça marche maintenant ?", cefr="A1"),
            ],
        )
    )

    assert m.Exemple.objects.count() == 3, "une phrase, un exemple, même à deux entrées"
    premier = m.Exemple.objects.get(phrase="Il travaille actuellement à Bruxelles.")
    assert premier.niveau == "A2"
    traduction = premier.traductions.get()
    assert (traduction.langue, traduction.traduction) == (
        "en",
        "He's currently working in Brussels.",
    )
    rattachements = set(
        m.ExempleEntree.objects.values_list(
            "exemple__phrase", "entree__slug", "surlignage", "ordre"
        )
    )
    assert rattachements == {
        ("Il travaille actuellement à Bruxelles.", "actuellement", "actuellement", 1),
        ("En fait, il vit actuellement à Genève.", "actuellement", "actuellement", 2),
        ("En fait, il vit actuellement à Genève.", "en-fait", "En fait", 1),
    }
    sans_etiquette = m.Exemple.objects.get(phrase="Est-ce que ça marche maintenant ?")
    assert not sans_etiquette.liens_entrees.exists()


def test_l_archive_zippee_s_importe_comme_le_dossier(tmp_path, db):
    racine = ecrire_archive(
        tmp_path,
        [fiche()],
        [
            phrase(
                "s000001", "Il m'a posé un lapin.", ("poser-un-lapin", "posé un lapin")
            )
        ],
    )
    chemin_du_zip = tmp_path / "donnees-initiales.zip"
    with zipfile.ZipFile(chemin_du_zip, "w") as archive:
        for fichier in racine.rglob("*.yaml"):
            archive.write(fichier, fichier.relative_to(tmp_path).as_posix())

    imp.importer(chemin_du_zip)
    assert (m.Entree.objects.count(), m.Exemple.objects.count()) == (1, 1)
    assert m.ExempleEntree.objects.get().surlignage == "posé un lapin"


def test_la_commande_rend_compte_en_francais(tmp_path, db):
    sortie = importer_par_la_commande(ecrire_archive(tmp_path, [fiche()]))
    assert "1 entrée, 1 piège, 0 exemple (0 rattachement à des entrées)" in sortie
    assert "0 lien entre entrées, 1 thème, 2 traductions anglaises." in sortie
    assert "brouillon" in sortie

    sortie = importer_par_la_commande(tmp_path / "donnees-initiales")
    assert "Rien de nouveau" in sortie
    assert (
        "1 entrée existait déjà et est restée telle quelle : poser-un-lapin" in sortie
    )


# --- Données erronées : rien n'est importé ------------------------------------


def verifier_que_rien_n_est_importe():
    assert all(modele.objects.count() == 0 for modele in MODELES_DE_CONTENU)
    assert not m.Theme.objects.exists()
    assert not get_user_model().objects.filter(username=imp.NOM_DU_COMPTE).exists()


def test_un_code_inconnu_arrete_tout(tmp_path, db):
    racine = ecrire_archive(tmp_path, [fiche("a"), fiche("b", pos="nounish")])
    with pytest.raises(CommandError) as erreur:
        importer_par_la_commande(racine)
    message = str(erreur.value)
    assert "data/items/b.yaml" in message
    assert "« pos »" in message
    assert "« nounish »" in message
    assert "Rien n'a été importé." in message
    verifier_que_rien_n_est_importe()


def test_un_code_repris_tel_quel_est_verifie_aussi(tmp_path, db):
    racine = ecrire_archive(tmp_path, [fiche(register="tres_poli")])
    with pytest.raises(CommandError, match="registre"):
        importer_par_la_commande(racine)
    verifier_que_rien_n_est_importe()


def test_un_surlignage_absent_de_la_phrase_arrete_tout(tmp_path, db):
    racine = ecrire_archive(
        tmp_path,
        [fiche()],
        [phrase("s000007", "Il n'est pas venu.", ("poser-un-lapin", "posé un lapin"))],
    )
    with pytest.raises(CommandError) as erreur:
        importer_par_la_commande(racine)
    assert "s000007" in str(erreur.value)
    assert "n'apparaît pas dans la phrase" in str(erreur.value)
    verifier_que_rien_n_est_importe()


def test_une_etiquette_vers_une_fiche_inconnue_arrete_tout(tmp_path, db):
    racine = ecrire_archive(
        tmp_path, [fiche()], [phrase("s000001", "Bonjour.", ("inconnue", "Bonjour"))]
    )
    with pytest.raises(CommandError, match="« inconnue »"):
        importer_par_la_commande(racine)
    verifier_que_rien_n_est_importe()


def test_un_lien_vers_une_fiche_inconnue_arrete_tout(tmp_path, db):
    racine = ecrire_archive(
        tmp_path, [fiche(related=[{"type": "contrast", "target": "inconnue"}])]
    )
    with pytest.raises(CommandError, match="« inconnue »"):
        importer_par_la_commande(racine)
    verifier_que_rien_n_est_importe()


def test_un_champ_obligatoire_qui_manque(tmp_path, db):
    donnees = fiche()
    del donnees["gloss_en"]
    with pytest.raises(CommandError, match="« gloss_en » manque"):
        importer_par_la_commande(ecrire_archive(tmp_path, [donnees]))
    verifier_que_rien_n_est_importe()


def test_un_fichier_yaml_illisible(tmp_path, db):
    racine = ecrire_archive(tmp_path, [fiche()])
    (racine / "data" / "items" / "casse.yaml").write_text("id: [pas fermé", "utf-8")
    with pytest.raises(CommandError, match="casse.yaml : fichier YAML illisible"):
        importer_par_la_commande(racine)
    verifier_que_rien_n_est_importe()


def test_un_chemin_qui_n_est_pas_une_archive(tmp_path, db):
    texte = tmp_path / "notes.txt"
    texte.write_text("rien à voir", "utf-8")
    for chemin in (texte, tmp_path / "absent.zip"):
        with pytest.raises(CommandError, match="n'est ni l'archive"):
            importer_par_la_commande(chemin)
    with pytest.raises(CommandError, match="Aucune fiche"):
        importer_par_la_commande(tmp_path)
    verifier_que_rien_n_est_importe()


# --- L'archive réelle ---------------------------------------------------------


@pytest.fixture
def archive_importee(db):
    return importer_par_la_commande(ARCHIVE)


def test_l_archive_donne_les_nombres_du_prd(archive_importee):
    assert "73 entrées, 85 pièges, 82 exemples (85 rattachements" in archive_importee
    assert m.Entree.objects.count() == 73
    assert m.Piege.objects.count() == 85
    assert m.Exemple.objects.count() == 82
    assert m.ExempleEntree.objects.count() == 85
    assert m.LienEntree.objects.count() == 26
    assert m.Theme.objects.count() == 17
    for traductions, attendu in [
        (m.EntreeTraduction, 73),
        (m.PiegeTraduction, 85),
        (m.ExempleTraduction, 82),
    ]:
        assert traductions.objects.filter(langue="en").count() == attendu


def test_tout_est_brouillon_marque_et_attribue_au_compte_d_import(archive_importee):
    compte = compte_d_import()
    for modele in MODELES_DE_CONTENU:
        assert set(modele.objects.values_list("statut", flat=True)) == {"brouillon"}
        assert set(modele.objects.values_list("genere_par_ia", flat=True)) == {True}
        assert set(modele.objects.values_list("ajoute_par", flat=True)) == {compte.pk}
        assert set(modele.history.values_list("history_user", flat=True)) == {compte.pk}
    for modele in AUTRES_MODELES:
        assert set(modele.objects.values_list("genere_par_ia", flat=True)) == {True}
        assert set(modele.history.values_list("history_user", flat=True)) == {compte.pk}


def test_les_explications_francaises_restent_vides(archive_importee):
    assert not any(p.explications() for p in m.Piege.objects.all())
    assert all(e.sens() for e in m.Entree.objects.all())


def test_les_precisions_de_l_archive_sont_en_francais(archive_importee):
    precisions = set(
        m.Entree.objects.exclude(precision="").values_list("precision", flat=True)
    )
    assert precisions == {
        "avant le nom",
        "après le nom",
        "d'accord",
        "affection",
        "prix",
        "Québec, Belgique, Suisse",
        "France",
        "X me manque",
        "rater un train, une occasion",
        "bêtises",
        "penser à",
        "penser de",
        "davantage",
        "ne… plus",
        "accomplir",
        "se rendre compte",
    }


def test_le_compte_d_import_ne_peut_pas_se_connecter(archive_importee):
    compte = compte_d_import()
    assert not compte.is_active
    assert not compte.has_usable_password()
    assert not compte.is_staff


def test_relancer_ne_remet_pas_ce_qu_on_a_retire_entre_contenus_existants(
    archive_importee,
):
    """Une entrée déjà là reste telle quelle, liens compris : un lien retiré le reste."""
    rattachement = m.ExempleEntree.objects.get(
        entree__slug="actuellement", exemple__phrase__startswith="Il travaille"
    )
    rattachement.delete()
    m.LienEntree.objects.filter(entree__slug="ancien-avant-nom").delete()
    avant = nombres()

    sortie = importer_par_la_commande(ARCHIVE)

    assert nombres() == avant
    assert "Rien de nouveau" in sortie


def test_lancer_deux_fois_ne_change_rien(archive_importee):
    avant = nombres()
    sortie = importer_par_la_commande(ARCHIVE)
    assert nombres() == avant
    assert "Rien de nouveau" in sortie
    assert "73 entrées existaient déjà" in sortie


def test_une_entree_supprimee_revient_avec_ses_pieges_ses_liens_et_ses_exemples(
    archive_importee,
):
    def rattachements():
        return Counter(
            m.ExempleEntree.objects.values_list(
                "exemple__phrase", "entree__slug", "surlignage", "ordre"
            )
        )

    def liens():
        return Counter(
            m.LienEntree.objects.values_list("entree__slug", "cible__slug", "type_lien")
        )

    avant = (rattachements(), liens(), m.Piege.objects.count())
    entree = m.Entree.objects.get(slug="en-fait")
    assert entree.liens_exemples.exists() and entree.liens_entrants.exists()
    pieges = entree.pieges.count()
    entree.delete()
    assert m.Exemple.objects.count() == 82, "les phrases restent"

    sortie = importer_par_la_commande(ARCHIVE)

    assert f"1 entrée, {pieges} piège" in sortie
    assert (rattachements(), liens(), m.Piege.objects.count()) == avant
    assert m.Exemple.objects.count() == 82, "aucune phrase en double"


def test_une_entree_faite_a_la_main_est_laissee_telle_quelle(db, proprietaire):
    a_la_main = creer_entree(
        proprietaire, slug="en-fait", vedette="en fait", sens_b1="Ce que j'ai écrit."
    )
    fiches, lots = imp.lire_archive(ARCHIVE)
    etiquettes = sum(
        etiquette["item"] == "en-fait"
        for _nom, lot in lots
        for p in lot["sentences"]
        for etiquette in p.get("tags", [])
    )

    sortie = importer_par_la_commande(ARCHIVE)

    a_la_main.refresh_from_db()
    assert not a_la_main.genere_par_ia
    assert a_la_main.sens_b1 == "Ce que j'ai écrit."
    assert not a_la_main.pieges.exists()
    assert not a_la_main.traductions.exists()
    assert not a_la_main.liens_exemples.exists()
    assert not a_la_main.liens_sortants.exists()
    assert not a_la_main.liens_entrants.exists()
    assert a_la_main.history.count() == 1, "personne d'autre ne l'a modifiée"
    assert m.Entree.objects.count() == 73
    assert m.Exemple.objects.count() == 82
    assert m.ExempleEntree.objects.count() == 85 - etiquettes
    assert "1 entrée existait déjà et est restée telle quelle : en-fait" in sortie
    assert len(fiches) == 73

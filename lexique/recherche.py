"""Textes dans toutes les écritures : normalisation, recherche et tri.

Règles de la section « Every alphabet » du PRD :

- tout texte enregistré est en Unicode NFC ;
- la recherche passe par un champ précalculé, ``recherche``, construit ici en
  Python : SQLite ne confond majuscules et minuscules que pour les lettres ASCII
  sans accent (« É » et « é », « К » et « к » ne se trouveraient pas) ;
- les accents ne sont retirés que du français (*être* → *etre*) : ailleurs, un
  signe change la lettre (l'ukrainien *й* n'est pas *и*, le polonais *ł* reste *ł*) ;
- le tri suit l'alphabet de chaque langue, grâce à ICU (en polonais, *ł* vient
  après *l*, pas après *z*).
"""

import unicodedata
from functools import cache

import icu
from django.db.models import Q

FRANCAIS = "fr"
NIVEAUX = ("a1", "a2", "b1", "b2", "c1", "c2")

#: Apostrophes typographiques, remplacées par l'apostrophe droite dans les textes
#: qu'on cherche et qu'on surligne (formes, phrases des exemples, surlignages).
APOSTROPHES_TYPOGRAPHIQUES = str.maketrans({"’": "'", "ʼ": "'"})

#: Pour chercher, toutes les façons de taper une apostrophe se valent (l'ukrainien
#: s'écrit avec ', ’, ʼ ou même `).
VARIANTES_D_APOSTROPHE = str.maketrans({caractere: "'" for caractere in "’‘ʼʹ´`′"})

LIGATURES = str.maketrans({"œ": "oe", "æ": "ae"})


# --- Normalisation ------------------------------------------------------------


def nfc(texte):
    """Le texte en Unicode NFC : « é » toujours en un seul caractère."""
    return unicodedata.normalize("NFC", texte)


def apostrophes_droites(texte):
    """Remplace les apostrophes typographiques (’) par l'apostrophe droite (')."""
    return texte.translate(APOSTROPHES_TYPOGRAPHIQUES)


def sans_accents_latins(texte):
    """Retire les accents des lettres latines, et seulement d'elles.

    Un mot ukrainien cité dans un texte français garde ainsi son *й*.
    """
    resultat = []
    base_latine = False
    for caractere in unicodedata.normalize("NFD", texte):
        if unicodedata.combining(caractere):
            if not base_latine:
                resultat.append(caractere)
            continue
        base_latine = unicodedata.name(caractere, "").startswith("LATIN ")
        resultat.append(caractere)
    return nfc("".join(resultat))


# --- Recherche ----------------------------------------------------------------


def cle_de_recherche(texte, langue):
    """La forme sous laquelle un texte est cherché, dans sa langue.

    NFC, apostrophes unifiées, casse ignorée (``casefold``), espaces réduites.
    Pour le français seulement : sans accents ni ligatures (*Être* → *etre*,
    *cœur* → *coeur*).
    """
    texte = nfc(texte).translate(VARIANTES_D_APOSTROPHE).casefold()
    if langue == FRANCAIS:
        texte = sans_accents_latins(texte).translate(LIGATURES)
    return " ".join(texte.split())


def _joindre(textes, langue):
    return "\n".join(
        cle for texte in textes if texte and (cle := cle_de_recherche(texte, langue))
    )


def recherche_de_l_entree(entree):
    """Le champ ``recherche`` d'une entrée : sa vedette, ses formes et ses sens."""
    sens = [getattr(entree, f"sens_{niveau}") for niveau in NIVEAUX]
    return _joindre([entree.vedette, *entree.formes, *sens], FRANCAIS)


def recherche_de_la_traduction(traduction):
    """Le champ ``recherche`` d'une traduction d'entrée : son sens, dans sa langue."""
    return _joindre([traduction.sens], traduction.langue)


def mots(requete, langue):
    """Les mots d'une requête, sous leur forme de recherche."""
    return cle_de_recherche(requete, langue).split()


def contient_tous_les_mots(liste_de_mots):
    """Filtre : le champ ``recherche`` contient chacun des mots, dans n'importe quel ordre."""
    filtre = Q()
    for mot in liste_de_mots:
        filtre &= Q(recherche__contains=mot)
    return filtre


def chercher(requete, langue=FRANCAIS, entrees=None, traductions=None):
    """Les entrées qui contiennent tous les mots de la requête, les plus proches d'abord.

    La requête est cherchée dans le texte français des entrées (vedette, formes,
    sens) et, si ``langue`` n'est pas le français, dans leurs traductions dans
    cette langue. ``entrees`` et ``traductions`` restreignent la recherche (au
    contenu relu, sur le site public).

    Ordre des résultats : d'abord une vedette ou une forme identique à la
    requête, puis une vedette ou une forme qui la contient, puis le reste ;
    à rang égal, l'ordre alphabétique français.
    """
    from lexique.models import Entree, EntreeTraduction

    mots_francais = mots(requete, FRANCAIS)
    if not mots_francais:
        return []
    entrees = Entree.objects.all() if entrees is None else entrees
    trouvees = contient_tous_les_mots(mots_francais)
    if langue != FRANCAIS:
        traductions = (
            EntreeTraduction.objects.all() if traductions is None else traductions
        )
        dans_la_langue = traductions.filter(langue=langue).filter(
            contient_tous_les_mots(mots(requete, langue))
        )
        trouvees |= Q(pk__in=dans_la_langue.values("entree"))

    cle = cle_de_recherche(requete, FRANCAIS)

    def rang(entree):
        noms = [
            cle_de_recherche(nom, FRANCAIS) for nom in [entree.vedette, *entree.formes]
        ]
        if cle in noms:
            return 0
        if any(cle in nom for nom in noms):
            return 1
        return 2

    return sorted(
        entrees.filter(trouvees).distinct(),
        key=lambda entree: (rang(entree), bytes(entree.cle_de_tri)),
    )


# --- Tri ----------------------------------------------------------------------


@cache
def collateur(langue):
    """Le collateur ICU d'une langue (ordre racine d'Unicode si ICU ne la connaît pas)."""
    return icu.Collator.createInstance(icu.Locale(langue or "root"))


def cle_de_tri(*textes, langue):
    """Clé de tri (des octets) selon l'alphabet de la langue.

    Plusieurs textes se trient l'un après l'autre : la vedette, puis la précision.
    Les octets se comparent tels quels, en Python comme dans la base de données.
    """
    regles = collateur(langue)
    return b"".join(regles.getSortKey(nfc(texte or "")) for texte in textes)


def cle_de_tri_de_l_entree(entree):
    """Clé de tri d'une entrée : sa vedette, puis sa précision, dans l'ordre français."""
    return cle_de_tri(entree.vedette, entree.precision, langue=FRANCAIS)


def trier(elements, langue, cle=str):
    """Trie ``elements`` selon l'alphabet de ``langue`` ; ``cle`` donne le texte de chacun."""
    return sorted(elements, key=lambda element: cle_de_tri(cle(element), langue=langue))


# --- Reconstruction -----------------------------------------------------------


def reconstruire(modele_entree, modele_traduction):
    """Recalcule les champs ``recherche`` et ``cle_de_tri`` qui ne sont plus à jour.

    Sert après un changement des règles ou d'ICU (les clés de tri en dépendent).
    Ne touche ni au texte, ni au statut, ni à l'historique : rien n'est
    enregistré par ``save()``. Prend les modèles en paramètre pour servir aussi
    dans les migrations. Renvoie le nombre d'entrées et de traductions mises à jour.
    """
    entrees = []
    for entree in modele_entree.objects.all():
        recherche = recherche_de_l_entree(entree)
        cle = cle_de_tri_de_l_entree(entree)
        if entree.recherche != recherche or bytes(entree.cle_de_tri) != cle:
            entree.recherche, entree.cle_de_tri = recherche, cle
            entrees.append(entree)
    modele_entree.objects.bulk_update(
        entrees, ["recherche", "cle_de_tri"], batch_size=500
    )

    traductions = []
    for traduction in modele_traduction.objects.all():
        recherche = recherche_de_la_traduction(traduction)
        if traduction.recherche != recherche:
            traduction.recherche = recherche
            traductions.append(traduction)
    modele_traduction.objects.bulk_update(traductions, ["recherche"], batch_size=500)
    return len(entrees), len(traductions)

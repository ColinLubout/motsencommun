"""Administration du lexique : le contenu, son historique et ses relectures."""

from urllib.parse import urlencode

from django import forms
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from lexique import models as m
from lexique import recherche
from lexique import vocabulaire as v

#: Les statuts qu'on choisit à la main ; « relu », « validé » et « refusé » viennent des relectures.
STATUTS_MANUELS = [v.Statut.BROUILLON, v.Statut.EN_RELECTURE]
CHAMPS_DU_SENS = [f"sens_{n.lower()}" for n in v.NIVEAUX]
CHAMPS_DE_L_EXPLICATION = [f"explication_{n.lower()}" for n in v.NIVEAUX]


class RelectureInline(GenericTabularInline):
    """Les relectures d'un contenu, en lecture seule."""

    model = m.Relecture
    ct_field = "type_contenu"
    ct_fk_field = "id_contenu"
    fields = ("date", "decision", "relecteur", "commentaire")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class AdminContenu(SimpleHistoryAdmin):
    """Ce qui est commun aux contenus relus : statut, auteur, historique et relectures."""

    readonly_fields = (
        "genere_par_ia",
        "relire",
        "ajoute_par",
        "cree_le",
        "modifie_le",
        "texte_modifie_le",
    )
    list_filter = ("statut", "genere_par_ia")
    inlines = [RelectureInline]
    champs_du_suivi = (
        "statut",
        "genere_par_ia",
        "relire",
        "ajoute_par",
        "cree_le",
        "modifie_le",
        "texte_modifie_le",
    )

    @admin.display(description=_("relecture"))
    def relire(self, obj):
        if obj is None or obj.pk is None:
            return "—"
        parametres = urlencode(
            {
                "type_contenu": ContentType.objects.get_for_model(obj).pk,
                "id_contenu": obj.pk,
            }
        )
        adresse = f"{reverse('admin:lexique_relecture_add')}?{parametres}"
        return format_html('<a href="{}">{}</a>', adresse, _("Relire ce contenu"))

    def get_form(self, request, obj=None, **kwargs):
        formulaire = super().get_form(request, obj, **kwargs)
        champ = formulaire.base_fields.get("statut")
        if champ is not None:
            permis = list(STATUTS_MANUELS)
            if request.user.is_superuser:
                permis.append(v.Statut.RETIRE)
            if obj is not None and obj.statut not in permis:
                permis.append(obj.statut)
            champ.choices = [
                (code, nom) for code, nom in v.Statut.choices if code in permis
            ]
            champ.help_text = _(
                "« Relu », « validé » et « refusé » viennent des relectures. "
                "Modifier le texte d'un contenu relu le renvoie en relecture."
            )
        return formulaire

    def save_model(self, request, obj, form, change):
        if not change:
            obj.ajoute_par = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, m.Contenu) and instance.ajoute_par_id is None:
                instance.ajoute_par = request.user
            instance.save()
        for supprime in formset.deleted_objects:
            supprime.delete()
        formset.save_m2m()


# --- Entrées ------------------------------------------------------------------


class PiegeInline(admin.StackedInline):
    model = m.Piege
    extra = 0
    show_change_link = True
    fields = (
        ("type_piege", "gravite"),
        "concerne",
        ("langue_apprenant", "declencheur"),
        *CHAMPS_DE_L_EXPLICATION,
        ("incorrect", "correct"),
    )


class ExempleDeLEntreeInline(admin.TabularInline):
    model = m.ExempleEntree
    fk_name = "entree"
    extra = 0
    fields = ("exemple", "surlignage", "ordre")
    autocomplete_fields = ("exemple",)
    verbose_name = _("exemple")
    verbose_name_plural = _("exemples")


class EntreeTraductionInline(admin.StackedInline):
    model = m.EntreeTraduction
    extra = 0
    show_change_link = True
    fields = ("langue", "sens", "sens_litteral")


class LienEntreeInline(admin.TabularInline):
    model = m.LienEntree
    fk_name = "entree"
    extra = 0
    fields = ("type_lien", "cible")
    autocomplete_fields = ("cible",)


@admin.register(m.Entree)
class EntreeAdmin(AdminContenu):
    list_display = (
        "vedette",
        "precision",
        "niveau",
        "statut",
        "genere_par_ia",
        "modifie_le",
    )
    list_filter = (
        "statut",
        "niveau",
        "type_entree",
        "registre",
        "themes",
        "genere_par_ia",
    )
    search_fields = ("vedette", "precision", "slug")
    filter_horizontal = ("themes",)

    def get_search_results(self, request, queryset, search_term):
        """Comme sur le site : sans casse ni accents (« etre » trouve « Être »), tous les mots.

        Sert aussi aux listes à compléter des liens et des exemples.
        """
        resultats, doublons = super().get_search_results(request, queryset, search_term)
        mots = recherche.mots(search_term, recherche.FRANCAIS)
        if mots:
            resultats |= queryset.filter(recherche.contient_tous_les_mots(mots))
        return resultats, doublons

    fieldsets = (
        (None, {"fields": ("vedette", "precision", "slug")}),
        (
            _("Description"),
            {
                "fields": (
                    ("type_entree", "nature", "genre"),
                    ("niveau", "registre", "frequence"),
                    "api",
                    "regions",
                    "themes",
                    "formes",
                )
            },
        ),
        (
            _("Sens, en français, par niveau"),
            {"fields": (*CHAMPS_DU_SENS, "sens_litteral")},
        ),
        (_("Suivi"), {"fields": AdminContenu.champs_du_suivi}),
    )
    inlines = [
        PiegeInline,
        ExempleDeLEntreeInline,
        EntreeTraductionInline,
        LienEntreeInline,
        RelectureInline,
    ]

    def get_readonly_fields(self, request, obj=None):
        champs = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            champs.append("slug")  # le slug ne change jamais
        return champs


# --- Pièges, exemples, traductions --------------------------------------------


class PiegeTraductionInline(admin.StackedInline):
    model = m.PiegeTraduction
    extra = 0
    show_change_link = True
    fields = ("langue", "explication")


@admin.register(m.Piege)
class PiegeAdmin(AdminContenu):
    list_display = ("__str__", "gravite", "statut", "genere_par_ia", "modifie_le")
    list_filter = ("statut", "type_piege", "gravite", "genere_par_ia")
    search_fields = ("entree__vedette", "declencheur")
    autocomplete_fields = ("entree",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "entree",
                    ("type_piege", "gravite"),
                    "concerne",
                    ("langue_apprenant", "declencheur"),
                )
            },
        ),
        (
            _("Explication, en français, par niveau"),
            {"fields": CHAMPS_DE_L_EXPLICATION},
        ),
        (_("Paire minimale"), {"fields": ("incorrect", "correct")}),
        (_("Suivi"), {"fields": AdminContenu.champs_du_suivi}),
    )
    inlines = [PiegeTraductionInline, RelectureInline]


class EntreeDeLExempleInline(admin.TabularInline):
    model = m.ExempleEntree
    fk_name = "exemple"
    extra = 0
    fields = ("entree", "surlignage", "ordre")
    autocomplete_fields = ("entree",)
    verbose_name = _("entrée illustrée")
    verbose_name_plural = _("entrées illustrées")


class ExempleTraductionInline(admin.StackedInline):
    model = m.ExempleTraduction
    extra = 0
    show_change_link = True
    fields = ("langue", "traduction")


@admin.register(m.Exemple)
class ExempleAdmin(AdminContenu):
    list_display = ("phrase", "niveau", "statut", "genere_par_ia", "modifie_le")
    list_filter = ("statut", "niveau", "genere_par_ia")
    search_fields = ("phrase",)
    fieldsets = (
        (None, {"fields": ("phrase", "niveau")}),
        (_("Suivi"), {"fields": AdminContenu.champs_du_suivi}),
    )
    inlines = [EntreeDeLExempleInline, ExempleTraductionInline, RelectureInline]

    def save_model(self, request, obj, form, change):
        # Pour une modification, l'exemple s'enregistre après ses liens (voir save_related) :
        # on peut ainsi changer la phrase et ses surlignages en même temps.
        if not change:
            super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        if not change:
            super().save_related(request, form, formsets, change)
            return
        for formset in formsets:
            self.save_formset(request, form, formset, change)
        form.instance.save()
        form.save_m2m()


class AdminTraduction(AdminContenu):
    list_display = ("__str__", "langue", "statut", "genere_par_ia", "modifie_le")
    list_filter = ("statut", "langue", "genere_par_ia")


@admin.register(m.EntreeTraduction)
class EntreeTraductionAdmin(AdminTraduction):
    search_fields = ("entree__vedette", "sens")
    autocomplete_fields = ("entree",)
    fieldsets = (
        (None, {"fields": ("entree", "langue", "sens", "sens_litteral")}),
        (_("Suivi"), {"fields": AdminContenu.champs_du_suivi}),
    )


@admin.register(m.PiegeTraduction)
class PiegeTraductionAdmin(AdminTraduction):
    search_fields = ("piege__entree__vedette", "explication")
    autocomplete_fields = ("piege",)
    fieldsets = (
        (None, {"fields": ("piege", "langue", "explication")}),
        (_("Suivi"), {"fields": AdminContenu.champs_du_suivi}),
    )


@admin.register(m.ExempleTraduction)
class ExempleTraductionAdmin(AdminTraduction):
    search_fields = ("exemple__phrase", "traduction")
    autocomplete_fields = ("exemple",)
    fieldsets = (
        (None, {"fields": ("exemple", "langue", "traduction")}),
        (_("Suivi"), {"fields": AdminContenu.champs_du_suivi}),
    )


# --- Thèmes et liens ----------------------------------------------------------


class ThemeTraductionInline(admin.TabularInline):
    model = m.ThemeTraduction
    extra = 0
    fields = ("langue", "nom")


@admin.register(m.Theme)
class ThemeAdmin(SimpleHistoryAdmin):
    list_display = ("nom", "slug", "genere_par_ia")
    search_fields = ("nom", "slug")
    prepopulated_fields = {"slug": ("nom",)}
    readonly_fields = ("genere_par_ia",)
    inlines = [ThemeTraductionInline]


@admin.register(m.ThemeTraduction)
class ThemeTraductionAdmin(SimpleHistoryAdmin):
    list_display = ("theme", "langue", "nom", "genere_par_ia")
    readonly_fields = ("genere_par_ia",)


@admin.register(m.LienEntree)
class LienEntreeAdmin(SimpleHistoryAdmin):
    list_display = ("entree", "type_lien", "cible", "genere_par_ia")
    autocomplete_fields = ("entree", "cible")
    readonly_fields = ("genere_par_ia",)


@admin.register(m.ExempleEntree)
class ExempleEntreeAdmin(SimpleHistoryAdmin):
    list_display = ("entree", "surlignage", "exemple", "genere_par_ia")
    autocomplete_fields = ("entree", "exemple")
    readonly_fields = ("genere_par_ia",)


# --- Contributeurs et relectures ----------------------------------------------


@admin.register(m.Contributeur)
class ContributeurAdmin(SimpleHistoryAdmin):
    list_display = ("nom_affiche", "utilisateur", "relit_langues")
    search_fields = ("nom_affiche", "utilisateur__username")
    readonly_fields = ("utilisateur",)

    def has_add_permission(self, request):
        return False  # chaque compte reçoit son profil automatiquement


@admin.register(m.Relecture)
class RelectureAdmin(SimpleHistoryAdmin):
    list_display = ("date", "decision", "contenu", "relecteur")
    list_filter = ("decision",)
    fields = ("type_contenu", "id_contenu", "decision", "commentaire")

    def get_form(self, request, obj=None, **kwargs):
        formulaire = super().get_form(request, obj, **kwargs)
        if obj is not None:
            return formulaire

        class FormulaireRelecture(formulaire):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.instance.relecteur = request.user
                for nom in ("type_contenu", "id_contenu"):
                    self.fields[nom].widget = forms.HiddenInput()

        return FormulaireRelecture

    def has_change_permission(self, request, obj=None):
        return False  # une relecture ne se modifie pas

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.relecteur = request.user
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        """Après une relecture, on revient au contenu relu."""
        meta = obj.type_contenu.model_class()._meta
        return HttpResponseRedirect(
            reverse(
                f"admin:{meta.app_label}_{meta.model_name}_change",
                args=[obj.id_contenu],
            )
        )

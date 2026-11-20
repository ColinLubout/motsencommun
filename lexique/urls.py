"""Adresses des pages publiques, sous le préfixe de langue (voir motsencommun/urls.py)."""

from django.urls import path

from lexique import views

app_name = "lexique"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("expressions/", views.liste, name="liste"),
    path("expressions/<slug:slug>/", views.fiche, name="fiche"),
    path("niveau/<str:niveau>/", views.par_niveau, name="par_niveau"),
    path("type/<str:type_piege>/", views.par_type, name="par_type"),
    path("theme/<slug:slug>/", views.par_theme, name="par_theme"),
    path("recherche/", views.recherche, name="recherche"),
    path("telecharger/", views.telecharger, name="telecharger"),
    path("a-propos/", views.a_propos, name="a_propos"),
]

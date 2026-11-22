/* Mots en commun : le confort de lecture et « Mon niveau », retenus dans ce
   navigateur seulement (localStorage). Rien n'est envoyé au serveur : ni
   cookie, ni statistiques. Sans JavaScript, le site marche de la même façon ;
   seul le bouton du confort de lecture n'apparaît pas. */
(function () {
  "use strict";

  var racine = document.documentElement;
  var CONFORT = "mots-en-commun.confort-de-lecture";
  var MON_NIVEAU = "mots-en-commun.mon-niveau";
  var NIVEAUX = ["A1", "A2", "B1", "B2", "C1", "C2"];

  function lire(cle) {
    try {
      return window.localStorage.getItem(cle);
    } catch (erreur) {
      return null;
    }
  }

  function ecrire(cle, valeur) {
    try {
      if (valeur) {
        window.localStorage.setItem(cle, valeur);
      } else {
        window.localStorage.removeItem(cle);
      }
    } catch (erreur) {
      /* Stockage refusé (navigation privée…) : le choix vaut pour cette page. */
    }
  }

  /* Une page ouverte sans niveau reprend celui que le lecteur a choisi. */
  var adresse = new URL(window.location.href);
  var niveau = lire(MON_NIVEAU);
  if (NIVEAUX.indexOf(niveau) >= 0 && !adresse.searchParams.has("mon_niveau")) {
    adresse.searchParams.set("mon_niveau", niveau);
    window.location.replace(adresse.href);
    return;
  }

  /* Avant l'affichage, pour que la page ne change pas d'aspect sous les yeux. */
  if (lire(CONFORT) === "oui") {
    racine.classList.add("confort");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var bouton = document.getElementById("bouton-confort");
    if (bouton) {
      bouton.setAttribute("aria-pressed", String(racine.classList.contains("confort")));
      bouton.hidden = false;
      bouton.addEventListener("click", function () {
        var actif = racine.classList.toggle("confort");
        bouton.setAttribute("aria-pressed", String(actif));
        ecrire(CONFORT, actif ? "oui" : null);
      });
    }

    /* Le niveau choisi dans le sélecteur est retenu ; « celui de chaque entrée » l'oublie. */
    var formulaire = document.querySelector("form.mon-niveau");
    if (formulaire) {
      formulaire.addEventListener("submit", function () {
        var choix = formulaire.elements.mon_niveau.value;
        ecrire(MON_NIVEAU, NIVEAUX.indexOf(choix) >= 0 ? choix : null);
      });
    }
  });
})();

# Contribuer à Mots en commun

Merci de vouloir aider ! Ce guide explique comment proposer une modification du code. Les contributions au contenu (nouvelles expressions, traductions, relectures) passeront par le site lui-même, à partir de la phase 2.

Les issues et les pull requests peuvent être écrites en français ou en anglais.

## Avant de commencer

- Le cahier des charges, [docs/prd.md](docs/prd.md), fait référence. Si une modification s'en écarte, proposez d'abord de changer le cahier des charges, dans une issue.
- Pour une faille de sécurité, n'ouvrez pas d'issue publique : suivez [SECURITY.md](SECURITY.md).

## Préparer son poste

Installez [uv](https://docs.astral.sh/uv/), puis, à la racine du dépôt :

```sh
uv sync          # installe Python et les dépendances verrouillées dans uv.lock
uv run pytest    # tous les tests doivent passer
```

Sous Windows, Smart App Control peut bloquer Python et les outils du projet : travaillez alors dans WSL (le sous-système Windows pour Linux). Le script [outils/preparer-poste-windows.ps1](outils/preparer-poste-windows.ps1) installe Git, GitHub CLI, WSL2, Debian et uv, clone le dépôt et lance les tests. Il se relance sans risque ; sur un poste neuf, lancez-le une deuxième fois après le redémarrage qu'il demande :

```powershell
powershell -ExecutionPolicy Bypass -File outils\preparer-poste-windows.ps1
```

## Proposer une modification

1. Créez une branche à partir de `main`. Personne ne pousse directement sur `main` : tout passe par une pull request.
2. Faites des commits petits et ciblés, de préférence avec un message en français.
3. Avant chaque commit, lancez les tests et les vérifications :

   ```sh
   uv run pytest
   uv run ruff check
   uv run ruff format
   ```

4. Ouvrez une pull request qui explique ce qui change et comment c'est testé. L'intégration continue relance les tests, vérifie le style et cherche les failles connues des dépendances (pip-audit). La fusion demande des vérifications au vert et l'accord du propriétaire du projet.

## Règles du code

- **Noms en français**, en ASCII sans accents : modèles, champs, variables, fonctions, adresses, commandes, gabarits et classes CSS (`Entree`, `sens_b1`, `/fr/expressions/`). Les noms réservés de Django et de Python restent tels quels.
- **Commentaires et docstrings en français.**
- **Textes de l'interface** écrits en français et marqués pour la traduction (`gettext`, `{% translate %}`, `{% blocktranslate %}`). Dès qu'un nombre apparaît, utilisez les formes plurielles de Django : le polonais et l'ukrainien en ont plus de deux.
- **Tests** : chaque critère vérifiable par du code devient un test (pytest-django). Un test qui échoue bloque la fusion.
- **Migrations** : committées avec le code qui les demande, et jamais modifiées une fois publiées.
- **Dépendances** : le moins possible, toutes verrouillées dans `uv.lock` (`uv add` pour en ajouter une). Une nouvelle dépendance doit être vraiment nécessaire, et la pull request explique pourquoi. Les actions GitHub sont épinglées à un commit complet.

## Règles impératives

- **Aucun secret dans le dépôt** : ni clé, ni mot de passe, ni jeton. Les réglages viennent de variables d'environnement ; seul [deploiement/env.exemple](deploiement/env.exemple), avec des valeurs vides ou d'exemple, est versionné.
- **Vie privée** : les pages publiques ne posent aucun cookie et ne font aucune requête vers un autre site (ni CDN, ni police externe, ni statistiques). Rien n'enregistre l'adresse IP des visiteurs.
- **JavaScript** : seulement pour rendre le site plus agréable aux lecteurs, jamais pour les suivre. Les scripts sont des fichiers du site, jamais écrits dans le HTML, et chaque page fonctionne sans JavaScript.
- **Le texte des contributeurs n'est jamais du HTML** : pas de `|safe`, de `mark_safe` ni de `format_html` sur ces champs.
- **Seul le contenu relu est public** : ce qui n'est pas `relu` ou `valide` n'apparaît nulle part sur le site public, et son adresse renvoie une erreur 404.

## Traduire

- **L'interface** se traduit dans les fichiers `.po` du dossier `locale/`. Ces traductions s'ouvriront aux contributeurs en phase 2.
- **Le README** : voir la section « Traduire ce README » de [README.md](README.md). Si vous modifiez `README.md`, mettez à jour sa date de version.

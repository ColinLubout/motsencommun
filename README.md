# Mots en commun

*Les expressions françaises, expliquées par ceux qui les apprennent et ceux qui les parlent.*

Version de ce texte : 2026-11-22 · Traductions : [English](README.en.md)

**Mots en commun** est un site gratuit et auto-hébergé où les personnes qui apprennent le français et celles qui le parlent depuis toujours notent et retrouvent les expressions qui ne veulent pas dire ce que leurs mots laissent croire : *être en train de*, *en vouloir à quelqu'un*, *poser un lapin*… Chaque entrée donne une explication simple, son niveau, les pièges qu'elle tend et des phrases d'exemple. Toute la liste pourra être téléchargée en données structurées, pour construire d'autres outils d'apprentissage.

Le projet est porté par sa communauté et autofinancé. Il n'a ni publicité ni pistage, et aucun but commercial.

## Où en est le projet

Le site est en construction : c'est la phase 1, le site de base. Il sera annoncé quand assez d'entrées auront été relues pour valoir la visite. Le cahier des charges complet, en anglais, est dans [docs/prd.md](docs/prd.md).

## Principes

- **Le français d'abord.** Tout ce que le projet définit est nommé en français : tables, champs, adresses et interface. Les autres langues forment une couche à part, ajoutée par des contributeurs.
- **Tous les alphabets.** Les écritures latines, cyrilliques et de droite à gauche fonctionnent dès le départ.
- **Respect de la vie privée.** Pas de cookie sur les pages publiques, aucune requête vers d'autres sites, aucun pistage. Le JavaScript sert seulement à rendre le site plus agréable, jamais à suivre les lecteurs.
- **Simple et rapide.** Des pages HTML produites par le serveur, une seule petite feuille de style, et des pages qui fonctionnent sans JavaScript.
- **Rien ne se perd.** Chaque modification est enregistrée, avec qui l'a faite et quand.

## Licences

- **Le code** est sous licence MIT : voir [LICENCE-CODE](LICENCE-CODE).
- **Les données** (entrées, pièges, exemples, traductions et fichiers à télécharger) sont sous licence [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/deed.fr) (CC BY 4.0) : voir [LICENCE-DONNEES](LICENCE-DONNEES). Pour les réutiliser, créditez-les ainsi : *Contributeurs de Mots en commun*.

## Travailler sur le code

Il faut [uv](https://docs.astral.sh/uv/), qui installe lui-même la bonne version de Python et les dépendances verrouillées dans `uv.lock`. Il faut aussi la bibliothèque ICU, qui trie les mots selon l'alphabet de chaque langue (PyICU se compile contre elle à l'installation), et les outils gettext, qui compilent les traductions de l'interface.

- Debian ou Ubuntu : `sudo apt install libicu-dev pkg-config g++ gettext`
- macOS : `brew install icu4c pkg-config gettext`, puis `export PKG_CONFIG_PATH="$(brew --prefix icu4c)/lib/pkgconfig"` avant `uv sync`

```sh
uv sync              # crée l'environnement du projet (.venv)
uv run playwright install --with-deps chromium   # Chromium, pour les tests du navigateur
uv run pytest        # lance les tests (uv run pytest -m "not navigateur" : sans le navigateur, plus vite)
uv run ruff check    # vérifie le code
uv run ruff format   # met le code en forme
```

Pour lancer le site en local, activez le mode développement avec la variable `DJANGO_DEBUG=1` :

```sh
export DJANGO_DEBUG=1          # sous PowerShell : $env:DJANGO_DEBUG = "1"
uv run python manage.py migrate
uv run python manage.py compilemessages --ignore=.venv   # l'interface en anglais
uv run python manage.py createsuperuser
uv run python manage.py activer_double_authentification <votre-compte>
uv run python manage.py runserver
```

Le site est alors à l'adresse <http://127.0.0.1:8000/fr/> (et <http://127.0.0.1:8000/en/> en anglais), l'administration à <http://127.0.0.1:8000/admin/>. Le superutilisateur ne l'ouvre qu'avec la double authentification : `activer_double_authentification` affiche un QR code à scanner avec une application (Aegis, FreeOTP, Google Authenticator…), puis dix codes de secours.

Pour essayer le site avec du contenu, importez les données de départ :

```sh
uv run python manage.py importer_donnees_initiales donnees/import/donnees-initiales.zip
```

Elles ont été rédigées par une IA et ne servent qu'aux essais : tout arrive en brouillon, marqué « généré par IA », et le site en ligne est déployé sans elles. Sur le serveur, tous les réglages viennent de variables d'environnement, décrites dans [deploiement/env.exemple](deploiement/env.exemple).

Sous Windows, si Smart App Control bloque Python, travaillez dans WSL (le sous-système Windows pour Linux) : le script [outils/preparer-poste-windows.ps1](outils/preparer-poste-windows.ps1) installe et prépare tout.

## Contribuer

Les contributions au code sont ouvertes à tous : lisez [CONTRIBUTING.md](CONTRIBUTING.md). Les issues et les pull requests peuvent être écrites en français ou en anglais.

Pour signaler une faille de sécurité, n'ouvrez pas d'issue publique : suivez [SECURITY.md](SECURITY.md).

## Traduire ce README

Les traductions de ce fichier sont les bienvenues. Une pull request qui en ajoute une sera acceptée si elle suit ces règles :

- le fichier s'appelle `README.<code>.md`, où `<code>` est le code de la langue en deux lettres (ISO 639-1), le même que sur le site : `README.pl.md`, `README.uk.md` ;
- une variante régionale prend une étiquette BCP 47 : `README.pt-BR.md` ;
- la première ligne indique quelle version de `README.md` elle traduit (la date de la ligne « Version de ce texte »), pour qu'une traduction en retard se repère facilement ;
- la nouvelle langue est ajoutée à la liste des traductions, en haut de `README.md` et de chaque traduction.

Si vous modifiez `README.md`, mettez à jour sa date de version.

"""Réglages Django de Mots en commun.

Tout ce qui dépend de l'installation (clé secrète, noms de domaine, chemin de
l'administration, emplacement des données) vient de variables d'environnement,
lues par ``motsencommun.environnement`` et décrites dans
``deploiement/env.exemple``. Aucun secret n'est écrit ici.
"""

from pathlib import Path

from motsencommun.environnement import Environnement

BASE_DIR = Path(__file__).resolve().parent.parent

# Clé publique, connue de tous : elle ne sert qu'en développement local
# (DJANGO_DEBUG=1). Son préfixe « django-insecure- » fait échouer
# « manage.py check --deploy » si jamais elle arrivait sur un serveur.
CLE_DE_DEVELOPPEMENT = (
    "django-insecure-cle-publique-pour-le-developpement-local-uniquement"
)

env = Environnement()

DEBUG = env.developpement

SECRET_KEY = env.obligatoire("DJANGO_SECRET_KEY", en_developpement=CLE_DE_DEVELOPPEMENT)
ALLOWED_HOSTS = env.liste("DJANGO_ALLOWED_HOSTS", en_developpement=[])
CHEMIN_ADMIN = env.chemin_admin("CHEMIN_ADMIN")
DOSSIER_DONNEES = env.dossier("DOSSIER_DONNEES", en_developpement=BASE_DIR / "donnees")

# S'il manque une variable obligatoire, on s'arrête ici en les nommant toutes.
env.verifier()

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "lexique",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "motsencommun.urls"
WSGI_APPLICATION = "motsencommun.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Un seul fichier SQLite, en mode WAL : on peut lire pendant qu'on écrit. Les
# transactions démarrent en mode IMMEDIATE et attendent leur tour jusqu'à
# 20 secondes : les écritures des processus Gunicorn patientent au lieu
# d'échouer avec « database is locked ».
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DOSSIER_DONNEES / "base.sqlite3",
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL;",
            "transaction_mode": "IMMEDIATE",
            "timeout": 20,
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Le français d'abord. L'interface existe aussi en anglais ; d'autres langues
# s'ajoutent quand leurs traductions existent. Chaque langue est nommée dans sa
# propre langue, pour qu'on la reconnaisse sans savoir lire les autres.
LANGUAGE_CODE = "fr"
LANGUAGES = [
    ("fr", "Français"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True

# L'horloge du serveur est en UTC ; les dates s'affichent à l'heure de Paris.
TIME_ZONE = "Europe/Paris"
USE_TZ = True

STATIC_URL = "static/"

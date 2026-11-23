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
    # L'admin de Django, avec notre site (double authentification du superutilisateur).
    "motsencommun.apps.AdministrationConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "simple_history",
    "lexique",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CSP et Permissions-Policy, sur chaque page rendue par Django.
    "motsencommun.entetes.EntetesDeSecurite",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # La langue vient du préfixe de l'adresse ; l'administration reste en français.
    "motsencommun.langues.LangueDeLAdresse",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    # Retient qui fait chaque modification, pour l'historique.
    "simple_history.middleware.HistoryRequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "motsencommun.urls"
WSGI_APPLICATION = "motsencommun.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "motsencommun" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "lexique.contexte.site",
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

# Le cache est partagé entre les processus Gunicorn (fichiers dans DOSSIER_DONNEES) :
# le freinage des connexions ratées en dépend.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": DOSSIER_DONNEES / "cache",
    }
}

# Mots de passe : Argon2, au moins 16 caractères, sans maximum.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "motsencommun.mots_de_passe.LongueurMinimale",
        "OPTIONS": {"min_length": 16},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Sessions de l'administration : 12 heures au plus. Changer de mot de passe
# déconnecte les autres sessions (comportement de Django). Sur le serveur, les
# cookies ne passent qu'en HTTPS.
SESSION_COOKIE_AGE = 12 * 60 * 60
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# En-têtes de sécurité (les autres sont dans motsencommun/entetes.py).
# Caddy reçoit les visiteurs en HTTPS et le dit à Django par X-Forwarded-Proto ;
# Gunicorn n'écoute que sur une socket Unix, que seul Caddy atteint.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# HTTPS toujours, pendant un an, pour le domaine et ses sous-domaines (tous servis
# par Caddy, en HTTPS automatique). Pas d'inscription sur la liste de préchargement
# des navigateurs : elle se défait difficilement (PRD, « Privacy »).
SECURE_HSTS_SECONDS = 365 * 24 * 60 * 60
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SECURE_REFERRER_POLICY = "no-referrer"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SILENCED_SYSTEM_CHECKS = [
    # « SECURE_HSTS_PRELOAD n'est pas activé » : c'est voulu, voir plus haut.
    "security.W021",
]

# Le nom de l'émetteur affiché dans l'application de double authentification.
OTP_TOTP_ISSUER = "Mots en commun"

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
# Les fichiers que le site crée lui-même, comme les images d'aperçu des fiches.
# Sur le serveur, Caddy les sert directement.
MEDIA_URL = "/media/"
MEDIA_ROOT = DOSSIER_DONNEES / "media"
# La feuille de style unique du site (et, plus tard, ses polices).
STATICFILES_DIRS = [BASE_DIR / "static"]

#: Le dépôt du code : les failles s'y signalent en privé (SECURITY.md, security.txt).
DEPOT_DU_CODE = "https://github.com/ColinLubout/motsencommun"

#: Les robots qui collectent des textes pour entraîner une IA : robots.txt leur
#: demande de ne pas parcourir le site, et les envoie vers la page de
#: téléchargement, la voie prévue pour l'IA (données relues, structurées, créditées).
ROBOTS_D_ENTRAINEMENT_IA = [
    "GPTBot",
    "ClaudeBot",
    "anthropic-ai",
    "Google-Extended",
    "Applebot-Extended",
    "CCBot",
    "Bytespider",
    "Meta-ExternalAgent",
    "cohere-training-data-crawler",
    "AI2Bot",
]

#: Entrées par page dans les listes publiques.
ENTREES_PAR_PAGE = 50
#: Entrées récentes sur la page d'accueil.
ENTREES_RECENTES = 10

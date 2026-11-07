"""
Configuration Django commune à tous les environnements de NDEYAM AI.

Toutes les valeurs sensibles (clé secrète, base de données, clés API) sont lues
depuis les variables d'environnement ou le fichier backend/.env.
Aucune clé ne doit être écrite dans le code source.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173", "http://127.0.0.1:5173"]),
    DB_HOST=(str, "localhost"),
    DB_PORT=(int, 5432),
    JWT_ACCESS_MINUTES=(int, 15),
    JWT_REFRESH_DAYS=(int, 7),
    LLM_PROVIDER=(str, "none"),
    LLM_MODEL=(str, ""),
    LLM_API_KEY=(str, ""),
    LLM_BASE_URL=(str, ""),
    LLM_TIMEOUT_SECONDS=(int, 60),
    LLM_FALLBACKS=(bool, True),
    EMBEDDING_PROVIDER=(str, "none"),
    EMBEDDING_MODEL=(str, ""),
    EMBEDDING_API_KEY=(str, ""),
    EMBEDDING_BASE_URL=(str, ""),
    VECTOR_STORE_BACKEND=(str, "numpy"),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

APP_NAME = "NDEYAM AI"
APP_VERSION = "0.1.0"

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
]
LOCAL_APPS = [
    "core",
    "accounts",
    "governance",
    "farms",
    "animals",
    "nutrition",
    "formulations",
    "feeding",
    "growth",
    "alerts",
    "knowledge_base",
    "assistant",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Base de données : PostgreSQL uniquement ---------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "TEST": {"NAME": env("DB_TEST_NAME", default="test_ndeyamai")},
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalisation : interface en français, fuseau de Dakar -----------
LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français")]
TIME_ZONE = "Africa/Dakar"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ----------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    # "auth" : connexion, inscription, réinitialisation (protection contre le forçage des mots de passe)
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "600/minute",
        "auth": "10/minute",
        "assistant": "20/minute",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "NDEYAM AI — API",
    "DESCRIPTION": (
        "API REST de la plateforme NDEYAM AI (prototype). "
        "Les résultats du moteur de formulation sont des estimations mathématiques "
        "et non des recommandations validées, sauf mention explicite."
    ),
    "VERSION": APP_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "UserRoleEnum": "accounts.models.Role",
        "FarmMembershipRoleEnum": "farms.models.MembershipRole",
    },
}

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

# --- E-mail (réinitialisation du mot de passe) --------------------------------
# En développement, les e-mails sont affichés dans la console du serveur.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="NDEYAM AI <no-reply@localhost>")

# --- Intelligence artificielle (indépendante du fournisseur) -----------------
# LLM_PROVIDER : none | anthropic | openai_compatible | ollama
LLM = {
    "PROVIDER": env("LLM_PROVIDER").strip().lower(),
    "MODEL": env("LLM_MODEL"),
    "API_KEY": env("LLM_API_KEY"),
    "BASE_URL": env("LLM_BASE_URL"),
    "TIMEOUT_SECONDS": env("LLM_TIMEOUT_SECONDS"),
    # Claude uniquement : repli automatique côté serveur si une réponse est refusée par les classificateurs.
    "FALLBACKS": env("LLM_FALLBACKS"),
}
# EMBEDDING_PROVIDER : none | openai_compatible | ollama
EMBEDDINGS = {
    "PROVIDER": env("EMBEDDING_PROVIDER").strip().lower(),
    "MODEL": env("EMBEDDING_MODEL"),
    "API_KEY": env("EMBEDDING_API_KEY"),
    "BASE_URL": env("EMBEDDING_BASE_URL"),
}
# VECTOR_STORE_BACKEND : numpy (par défaut) | pgvector (prévu ultérieurement)
VECTOR_STORE_BACKEND = env("VECTOR_STORE_BACKEND").strip().lower()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name} — {message}", "style": "{"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}

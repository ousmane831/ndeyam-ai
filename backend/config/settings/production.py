"""Configuration de production : durcissement HTTPS et cookies."""

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, env

DEBUG = False

# Fichiers statiques (administration, documentation de l'API) servis par Django lui-même (whitenoise),
# juste après SecurityMiddleware. Ils sont rassemblés par « collectstatic » au déploiement.
MIDDLEWARE = [MIDDLEWARE[0], "whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE[1:]]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# Le contrôle de santé de l'hébergeur arrive en HTTP interne : pas de redirection pour lui.
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

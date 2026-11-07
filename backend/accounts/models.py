"""
Modèle utilisateur personnalisé.

Il est créé dès l'initialisation : Django impose que AUTH_USER_MODEL soit défini
avant la toute première migration. L'identifiant de connexion est l'adresse e-mail.
Les endpoints d'inscription, de connexion et de profil arrivent à l'étape 3.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrateur"
    ELEVEUR = "ELEVEUR", "Éleveur"
    EXPERT = "EXPERT", "Expert"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", Role.ELEVEUR)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.ADMIN)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Un superutilisateur doit avoir is_staff=True et is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("adresse e-mail", unique=True)
    role = models.CharField("rôle", max_length=16, choices=Role.choices, default=Role.ELEVEUR, db_index=True)
    phone = models.CharField("téléphone", max_length=32, blank=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["email"]

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def is_platform_admin(self) -> bool:
        return self.is_superuser or self.role == Role.ADMIN

    @property
    def is_expert(self) -> bool:
        return self.role == Role.EXPERT

    @property
    def is_breeder(self) -> bool:
        return self.role == Role.ELEVEUR

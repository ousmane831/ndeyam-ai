"""Fixtures partagées par les tests du backend."""

from contextlib import contextmanager

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone


@contextmanager
def rejected_by_database():
    """Vérifie qu'une opération est refusée par une contrainte PostgreSQL.

    Le bloc atomique évite de casser la transaction du test.
    """
    with pytest.raises(IntegrityError), transaction.atomic():
        yield


@pytest.fixture
def make_user(db, django_user_model):
    counter = {"n": 0}

    def _make(role="ELEVEUR", **kwargs):
        counter["n"] += 1
        return django_user_model.objects.create_user(
            email=kwargs.pop("email", f"user{counter['n']}@test.sn"),
            password="MotDePasse-Test-2026",
            role=role,
            **kwargs,
        )

    return _make


@pytest.fixture
def breeder(make_user):
    return make_user()


@pytest.fixture
def make_farm(db):
    from farms.models import Farm, FarmMembership

    def _make(owner=None, name=None, **kwargs):
        farm = Farm.objects.create(name=name or f"Ferme {Farm.objects.count() + 1}", **kwargs)
        if owner:
            FarmMembership.objects.create(farm=farm, user=owner, role="OWNER")
        return farm

    return _make


@pytest.fixture
def farm(make_farm, breeder):
    return make_farm(owner=breeder, name="Ferme de Thiès")


@pytest.fixture
def ovin(db):
    from animals.models import Species

    return Species.objects.get(code="OVIN")


@pytest.fixture
def source(db):
    from governance.models import SourceDocument

    return SourceDocument.objects.create(title="Source de test contrôlée", source_type="OTHER", year=2024)


@pytest.fixture
def validated_kwargs(source, make_user):
    """Champs nécessaires pour enregistrer une donnée de référence au statut VALIDÉ."""
    return {
        "status": "VALIDATED",
        "source": source,
        "validated_at": timezone.now(),
        "validated_by": make_user("EXPERT"),
    }


@pytest.fixture
def nutrient(db):
    from nutrition.models import Nutrient

    def _get(code, system=None):
        return (
            Nutrient.objects.get(code=code, system__code=system)
            if system
            else Nutrient.objects.get(code=code, system=None)
        )

    return _get


@pytest.fixture
def ingredient(db):
    from nutrition.models import Ingredient, IngredientCategory

    def _make(name="Ingrédient test", **kwargs):
        category = kwargs.pop("category", None) or IngredientCategory.objects.get(code="CEREALES")
        return Ingredient.objects.create(name=name, category=category, **kwargs)

    return _make


@pytest.fixture
def animal(farm, ovin):
    from animals.models import Animal

    return Animal.objects.create(farm=farm, species=ovin, tag_number="SN-001", sex="M")


@pytest.fixture
def api():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def client_for(db):
    """Client API authentifié avec un vrai jeton JWT pour l'utilisateur donné."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    def _client(user):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        return client

    return _client


@pytest.fixture
def make_composition(db, make_user):
    """Crée une composition VALIDÉE (valeurs de contrôle des tests, sans portée nutritionnelle)."""
    from governance.models import SourceDocument
    from nutrition.models import IngredientComposition

    source = SourceDocument.objects.create(title="Jeu de données de test contrôlé", source_type="OTHER")
    expert = make_user("EXPERT")

    def _make(ingredient, nutrient, value, **kwargs):
        defaults = {
            "status": "VALIDATED",
            "source": source,
            "validated_at": timezone.now(),
            "validated_by": expert,
        }
        return IngredientComposition.objects.create(
            ingredient=ingredient, nutrient=nutrient, value=value, **{**defaults, **kwargs}
        )

    return _make


@pytest.fixture
def expert(make_user):
    return make_user("EXPERT", email="expert@isra.sn")

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from accounts.models import Role

User = get_user_model()


@pytest.mark.django_db
def test_create_user_defaults_to_breeder_and_normalises_email():
    user = User.objects.create_user(email="Awa.Diop@Example.SN", password="MotDePasse-Solide-2026")
    assert user.email == "awa.diop@example.sn"
    assert user.role == Role.ELEVEUR
    assert user.is_breeder and not user.is_platform_admin
    assert user.check_password("MotDePasse-Solide-2026")
    assert not user.is_staff


@pytest.mark.django_db
def test_create_superuser_is_admin():
    admin = User.objects.create_superuser(email="admin@ndeyam.local", password="MotDePasse-Solide-2026")
    assert admin.role == Role.ADMIN
    assert admin.is_platform_admin and admin.is_staff and admin.is_superuser


@pytest.mark.django_db
def test_email_is_unique():
    User.objects.create_user(email="a@b.sn", password="x" * 12)
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="a@b.sn", password="y" * 12)


def test_email_required():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="x")

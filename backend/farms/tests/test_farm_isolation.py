import pytest

from conftest import rejected_by_database
from farms.models import Farm, FarmMembership

pytestmark = pytest.mark.django_db


def test_breeder_only_sees_own_farms(make_user, make_farm):
    alice, bob = make_user(), make_user()
    farm_a = make_farm(owner=alice, name="A")
    make_farm(owner=bob, name="B")
    assert list(Farm.objects.accessible_by(alice)) == [farm_a]


def test_inactive_membership_gives_no_access(make_user, make_farm):
    owner, former = make_user(), make_user()
    farm = make_farm(owner=owner)
    FarmMembership.objects.create(farm=farm, user=former, role="MANAGER", is_active=False)
    assert not Farm.objects.accessible_by(former).exists()


def test_expert_sees_only_farms_that_invited_him(make_user, make_farm):
    expert = make_user("EXPERT")
    farm = make_farm(owner=make_user())
    make_farm(owner=make_user())
    FarmMembership.objects.create(farm=farm, user=expert, role="EXPERT")
    assert list(Farm.objects.accessible_by(expert)) == [farm]
    assert not FarmMembership.objects.get(user=expert).can_write


def test_platform_admin_sees_all_farms(make_user, make_farm):
    make_farm(owner=make_user())
    make_farm(owner=make_user())
    assert Farm.objects.accessible_by(make_user("ADMIN")).count() == 2


def test_anonymous_sees_nothing(make_farm):
    from django.contrib.auth.models import AnonymousUser

    make_farm()
    assert not Farm.objects.accessible_by(AnonymousUser()).exists()


def test_a_farm_has_a_single_owner(make_user, make_farm):
    farm = make_farm(owner=make_user())
    with rejected_by_database():
        FarmMembership.objects.create(farm=farm, user=make_user(), role="OWNER")


def test_user_cannot_join_the_same_farm_twice(make_user, make_farm):
    user = make_user()
    farm = make_farm(owner=user)
    with rejected_by_database():
        FarmMembership.objects.create(farm=farm, user=user, role="MANAGER")

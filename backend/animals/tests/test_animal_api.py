import io
from datetime import timedelta

import pytest
from django.utils import timezone

from animals.models import Animal, AnimalGroup, Breed, Species
from farms.models import FarmMembership
from growth.models import Weighing

pytestmark = pytest.mark.django_db

ANIMALS = "/api/v1/animals/"
GROUPS = "/api/v1/groups/"


@pytest.fixture
def ctx(make_user, make_farm, ovin, client_for):
    alice, bob = make_user(email="alice@ferme.sn"), make_user(email="bob@ferme.sn")
    farm_a, farm_b = make_farm(owner=alice, name="A"), make_farm(owner=bob, name="B")
    animal_b = Animal.objects.create(farm=farm_b, species=ovin, tag_number="B-1", sex="F")
    return {
        "alice": alice,
        "bob": bob,
        "farm_a": farm_a,
        "farm_b": farm_b,
        "animal_b": animal_b,
        "client": client_for(alice),
        "ovin": ovin,
    }


def payload(ctx, **kw):
    return {"farm": ctx["farm_a"].pk, "tag_number": "SN-001", "species": ctx["ovin"].pk, "sex": "M", **kw}


# --- Création et validation ----------------------------------------------------------------


def test_create_animal(ctx):
    response = ctx["client"].post(
        ANIMALS, payload(ctx, name="Bélier 1", initial_weight_kg="32.5"), format="json"
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["species_name"] == "Ovin" and body["status"] == "ACTIVE" and body["last_weight"] is None
    assert body["uuid"]


def test_estimated_age_sets_estimated_birth_date(ctx):
    response = ctx["client"].post(ANIMALS, payload(ctx, estimated_age_months="6"), format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["birth_date_is_estimated"] is True
    assert 175 <= body["age_days"] <= 190


def test_birth_date_and_estimated_age_are_exclusive(ctx):
    response = ctx["client"].post(
        ANIMALS, payload(ctx, birth_date="2026-01-01", estimated_age_months="6"), format="json"
    )
    assert response.status_code == 400


def test_duplicate_tag_rejected_with_clear_message(ctx):
    ctx["client"].post(ANIMALS, payload(ctx), format="json")
    response = ctx["client"].post(ANIMALS, payload(ctx), format="json")
    assert response.status_code == 400
    assert "tag_number" in response.json()["errors"]


def test_breed_of_another_species_rejected(ctx):
    goat_breed = Breed.objects.create(species=Species.objects.get(code="CAPRIN"), name="Sahélienne test")
    response = ctx["client"].post(ANIMALS, payload(ctx, breed=goat_breed.pk), format="json")
    assert response.status_code == 400
    assert "breed" in response.json()["errors"]


def test_inactive_species_rejected(ctx):
    response = ctx["client"].post(
        ANIMALS, payload(ctx, species=Species.objects.get(code="BOVIN").pk), format="json"
    )
    assert response.status_code == 400
    assert "species" in response.json()["errors"]


def test_future_birth_date_rejected(ctx):
    future = (timezone.localdate() + timedelta(days=3)).isoformat()
    assert ctx["client"].post(ANIMALS, payload(ctx, birth_date=future), format="json").status_code == 400


# --- Isolation ---------------------------------------------------------------------------


def test_cannot_list_read_update_or_delete_other_farm_animals(ctx):
    client, other = ctx["client"], ctx["animal_b"]
    assert ctx["client"].get(ANIMALS).json()["count"] == 0
    assert client.get(f"{ANIMALS}{other.pk}/").status_code == 404
    assert client.patch(f"{ANIMALS}{other.pk}/", {"name": "x"}, format="json").status_code == 404
    assert client.delete(f"{ANIMALS}{other.pk}/").status_code == 404
    assert client.get(f"{ANIMALS}{other.pk}/history/").status_code == 404
    assert Animal.objects.filter(pk=other.pk).exists()


def test_cannot_create_animal_in_another_farm(ctx):
    response = ctx["client"].post(ANIMALS, payload(ctx, farm=ctx["farm_b"].pk), format="json")
    assert response.status_code == 400
    assert "farm" in response.json()["errors"]
    assert not Animal.objects.filter(farm=ctx["farm_b"], tag_number="SN-001").exists()


def test_cannot_put_animal_in_another_farms_group(ctx):
    foreign_group = AnimalGroup.objects.create(farm=ctx["farm_b"], name="Lot de Bob")
    response = ctx["client"].post(ANIMALS, payload(ctx, group=foreign_group.pk), format="json")
    assert response.status_code == 400
    assert "group" in response.json()["errors"]


def test_farm_cannot_be_changed_after_creation(ctx):
    animal_id = ctx["client"].post(ANIMALS, payload(ctx), format="json").json()["id"]
    ctx["client"].patch(f"{ANIMALS}{animal_id}/", {"farm": ctx["farm_b"].pk}, format="json")
    assert Animal.objects.get(pk=animal_id).farm == ctx["farm_a"]


def test_invited_expert_reads_but_cannot_write(ctx, expert, client_for):
    FarmMembership.objects.create(farm=ctx["farm_b"], user=expert, role="EXPERT")
    client = client_for(expert)
    assert client.get(f"{ANIMALS}{ctx['animal_b'].pk}/").status_code == 200
    assert client.patch(f"{ANIMALS}{ctx['animal_b'].pk}/", {"name": "x"}, format="json").status_code == 403
    assert client.post(ANIMALS, payload(ctx, farm=ctx["farm_b"].pk), format="json").status_code == 400


# --- Recherche, filtres, archivage --------------------------------------------------------


def test_search_filter_and_ordering(ctx):
    farm, ovin = ctx["farm_a"], ctx["ovin"]
    group = AnimalGroup.objects.create(farm=farm, name="Embouche")
    Animal.objects.create(farm=farm, species=ovin, tag_number="A-2", sex="F", name="Ndeye")
    Animal.objects.create(farm=farm, species=ovin, tag_number="A-1", sex="M", group=group)
    client = ctx["client"]
    assert [a["tag_number"] for a in client.get(ANIMALS).json()["results"]] == ["A-1", "A-2"]
    assert client.get(ANIMALS, {"search": "ndeye"}).json()["count"] == 1
    assert client.get(ANIMALS, {"sex": "M"}).json()["results"][0]["tag_number"] == "A-1"
    assert client.get(ANIMALS, {"group": group.pk}).json()["count"] == 1
    assert client.get(ANIMALS, {"group__isnull": "true"}).json()["count"] == 1


def test_archive_hides_from_default_list_and_restore(ctx):
    animal_id = ctx["client"].post(ANIMALS, payload(ctx), format="json").json()["id"]
    response = ctx["client"].post(
        f"{ANIMALS}{animal_id}/archive/", {"status": "SOLD", "note": "Vendu à la Tabaski"}, format="json"
    )
    assert response.status_code == 200 and response.json()["status"] == "SOLD"
    assert ctx["client"].get(ANIMALS).json()["count"] == 0
    assert ctx["client"].get(ANIMALS, {"status": "SOLD"}).json()["count"] == 1
    assert ctx["client"].post(f"{ANIMALS}{animal_id}/restore/").json()["status"] == "ACTIVE"


def test_history_merges_events_without_inventing_data(ctx):
    animal = Animal.objects.create(farm=ctx["farm_a"], species=ctx["ovin"], tag_number="H-1", sex="F")
    Weighing.objects.create(animal=animal, weight_kg=30, weighed_on=timezone.localdate() - timedelta(days=2))
    ctx["client"].post(
        f"{ANIMALS}{animal.pk}/observations/", {"text": "Bon appétit", "kind": "FEEDING"}, format="json"
    )
    events = ctx["client"].get(f"{ANIMALS}{animal.pk}/history/").json()
    assert {e["type"] for e in events} == {"weighing", "observation", "registration"}
    assert ctx["client"].get(f"{ANIMALS}{animal.pk}/").json()["last_weight"]["weight_kg"] == "30.00"


def test_observations_are_isolated(ctx):
    response = ctx["client"].post(
        f"{ANIMALS}{ctx['animal_b'].pk}/observations/", {"text": "x"}, format="json"
    )
    assert response.status_code == 404


# --- Lots -------------------------------------------------------------------------------------


def test_group_crud_and_unique_name(ctx):
    client = ctx["client"]
    response = client.post(GROUPS, {"farm": ctx["farm_a"].pk, "name": "Brebis gestantes"}, format="json")
    assert response.status_code == 201
    duplicate = client.post(GROUPS, {"farm": ctx["farm_a"].pk, "name": "brebis GESTANTES"}, format="json")
    assert duplicate.status_code == 400
    assert client.get(GROUPS).json()["results"][0]["animals_count"] == 0


# --- CSV ------------------------------------------------------------------------------------------


def test_export_csv(ctx):
    Animal.objects.create(
        farm=ctx["farm_a"], species=ctx["ovin"], tag_number="E-1", sex="F", initial_weight_kg="25.5"
    )
    response = ctx["client"].get(f"{ANIMALS}export/")
    assert response.status_code == 200
    content = response.content.decode("utf-8-sig")
    assert content.splitlines()[0].startswith("numero;nom;espece")
    assert "E-1" in content and "25,5" in content and "B-1" not in content


def csv_file(text, name="animaux.csv"):
    f = io.BytesIO(text.encode("utf-8"))
    f.name = name
    return f


def test_import_csv_reports_each_bad_line(ctx):
    text = (
        "numero;sexe;race;date_naissance;poids_initial_kg;lot\n"
        "I-1;F;Touabire;15/03/2025;28,5;Lot import\n"
        "I-2;X;;;;\n"
        "I-3;M;Race inconnue;;;\n"
        "I-1;M;;;;\n"
    )
    response = ctx["client"].post(
        f"{ANIMALS}import/", {"farm": ctx["farm_a"].pk, "file": csv_file(text)}, format="multipart"
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["created_rows"] == 1 and body["error_rows"] == 3
    assert [e["line"] for e in body["errors"]] == [3, 4, 5]
    animal = Animal.objects.get(tag_number="I-1")
    assert animal.breed.name == "Touabire" and str(animal.initial_weight_kg) == "28.50"
    assert animal.group.name == "Lot import"


def test_import_into_another_farm_is_refused(ctx):
    response = ctx["client"].post(
        f"{ANIMALS}import/",
        {"farm": ctx["farm_b"].pk, "file": csv_file("numero;sexe\nX;F\n")},
        format="multipart",
    )
    assert response.status_code == 400


def test_import_missing_columns(ctx):
    response = ctx["client"].post(
        f"{ANIMALS}import/", {"farm": ctx["farm_a"].pk, "file": csv_file("nom\nX\n")}, format="multipart"
    )
    assert response.status_code == 400
    assert "Colonnes obligatoires" in response.json()["detail"]


# --- Nomenclatures ---------------------------------------------------------------------------


def test_species_endpoint_lists_only_active_species(ctx):
    codes = [s["code"] for s in ctx["client"].get("/api/v1/species/").json()]
    assert codes == ["OVIN"]
    breeds = ctx["client"].get("/api/v1/breeds/", {"species": ctx["ovin"].pk}).json()
    assert len(breeds) == 5

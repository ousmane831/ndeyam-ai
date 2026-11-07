import pytest

from alerts.engine import evaluate_farm
from alerts.models import Alert
from farms.models import FarmMembership

pytestmark = pytest.mark.django_db

URL = "/api/v1/alerts/"
RULES = "/api/v1/alert-rules/"


@pytest.fixture
def alert(farm, animal):
    evaluate_farm(farm)  # l'animal du fixture est incomplet : alerte « informations manquantes »
    return Alert.objects.get(alert_type="MISSING_DATA")


def test_alerts_are_isolated(alert, client_for, breeder, make_user):
    assert client_for(breeder).get(URL).json()["count"] >= 1
    other = client_for(make_user())
    assert other.get(URL).json()["count"] == 0
    assert other.get(f"{URL}{alert.pk}/").status_code == 404
    assert other.post(f"{URL}{alert.pk}/resolve/").status_code == 404


def test_owner_resolves_and_list_hides_closed_by_default(alert, client_for, breeder):
    client = client_for(breeder)
    response = client.post(f"{URL}{alert.pk}/resolve/", {"note": "Infos ajoutées sur papier"}, format="json")
    assert response.status_code == 200 and response.json()["status"] == "RESOLVED"
    assert response.json()["resolved_by_email"] == breeder.email
    assert alert.pk not in [a["id"] for a in client.get(URL).json()["results"]]
    assert alert.pk in [a["id"] for a in client.get(URL, {"status": "RESOLVED"}).json()["results"]]


def test_invited_expert_sees_but_cannot_act(alert, client_for, expert, farm):
    FarmMembership.objects.create(farm=farm, user=expert, role="EXPERT")
    client = client_for(expert)
    assert client.get(f"{URL}{alert.pk}/").status_code == 200
    assert client.post(f"{URL}{alert.pk}/dismiss/").status_code == 403


def test_summary_and_explanation_fields(alert, client_for, breeder):
    client = client_for(breeder)
    summary = client.get(f"{URL}summary/").json()
    assert summary["open"] >= 1 and summary["by_type"]["MISSING_DATA"] == 1
    detail = client.get(f"{URL}{alert.pk}/").json()
    assert detail["rule_code"] and detail["trigger_data"]["missing_fields"]
    assert detail["target"]["type"] == "animal"


def test_evaluate_endpoint_limited_to_writable_farms(client_for, breeder, farm, animal, make_farm, make_user):
    client = client_for(breeder)
    assert client.post(f"{URL}evaluate/", {"farm": farm.pk}, format="json").status_code == 200
    foreign = make_farm(owner=make_user())
    assert client.post(f"{URL}evaluate/", {"farm": foreign.pk}, format="json").status_code == 403


# --- Règles ---------------------------------------------------------------------------------------


def test_farm_rule_parameters_are_validated(client_for, breeder, farm):
    client = client_for(breeder)
    base = {"farm": farm.pk, "alert_type": "WEIGHING_REMINDER"}
    assert client.post(RULES, {**base, "parameters": {"interval_days": 0}}, format="json").status_code == 400
    assert client.post(RULES, {**base, "parameters": {"inconnu": 1}}, format="json").status_code == 400
    created = client.post(RULES, {**base, "parameters": {"interval_days": 21}}, format="json")
    assert created.status_code == 201 and created.json()["name"] == "Rappel de pesée"
    assert client.post(RULES, {**base, "parameters": {"interval_days": 14}}, format="json").status_code == 400


def test_platform_rules_reserved_to_admins(client_for, breeder, make_user):
    data = {"alert_type": "WEIGHING_REMINDER", "parameters": {"interval_days": 45}}
    assert client_for(breeder).post(RULES, data, format="json").status_code == 403
    assert client_for(make_user("ADMIN")).post(RULES, data, format="json").status_code == 201


def test_rule_definitions_state_they_are_not_recommendations(client_for, breeder):
    definitions = client_for(breeder).get(f"{RULES}definitions/").json()
    weighing = next(d for d in definitions if d["alert_type"] == "WEIGHING_REMINDER")
    assert weighing["parameters"][0] == {
        "name": "interval_days",
        "default": 30,
        "min": 1,
        "max": 365,
        "label": "Intervalle entre deux pesées (jours)",
    }
    assert "pas des recommandations" in weighing["note"]


# --- Réévaluation immédiate après une action (défaut trouvé à l'étape 11) -----------------------


def test_submission_immediately_alerts_reviewers_and_decision_resolves(
    client_for, expert, ingredient, nutrient, source
):
    from nutrition.models import IngredientComposition

    composition = IngredientComposition.objects.create(
        ingredient=ingredient(name="Catalogue"),
        nutrient=nutrient("MAT"),
        value=100,
        source=source,
        created_by=expert,
    )
    client = client_for(expert)
    assert client.post(f"/api/v1/compositions/{composition.pk}/submit/").status_code == 200
    pending = Alert.objects.filter(alert_type="REFERENCE_TO_VALIDATE", recipient=expert, status="OPEN")
    assert pending.count() == 1 and "1 donnée(s)" in pending.get().title
    assert (
        client.post(
            f"/api/v1/compositions/{composition.pk}/validate/", {"comment": "ok"}, format="json"
        ).status_code
        == 200
    )
    assert not pending.exists()


def test_formula_review_request_immediately_alerts_farm(client_for, breeder, expert, farm, ovin):
    from formulations.models import FeedFormula

    FarmMembership.objects.create(farm=farm, user=expert, role="EXPERT")
    formula = FeedFormula.objects.create(
        farm=farm, name="À vérifier", species=ovin, mode="ECONOMIC", status="ESTIMATED"
    )
    assert client_for(breeder).post(f"/api/v1/formulas/{formula.pk}/submit-review/").status_code == 200
    review = Alert.objects.filter(alert_type="FORMULA_TO_REVIEW", farm=farm, status="OPEN")
    assert review.count() == 1
    response = client_for(expert).post(
        f"/api/v1/formulas/{formula.pk}/reject/", {"comment": "À revoir"}, format="json"
    )
    assert response.status_code == 200
    assert not review.exists()

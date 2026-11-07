from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from alerts.engine import NOT_A_DIAGNOSIS, evaluate_farm, evaluate_reviewers
from alerts.models import Alert, AlertRule
from feeding.models import FeedingRecord, Ration
from formulations.models import FeedFormula
from growth.models import GrowthMonitoringRange, Weighing
from nutrition.models import IngredientComposition

pytestmark = pytest.mark.django_db
TODAY = timezone.localdate()


def ago(days):
    return TODAY - timedelta(days=days)


def open_alerts(alert_type):
    return Alert.objects.filter(alert_type=alert_type, status__in=["OPEN", "ACKNOWLEDGED"])


@pytest.fixture
def complete_animal(animal, ovin):
    """Animal sans information manquante, pour isoler les autres règles."""
    animal.birth_date = ago(200)
    animal.category = ovin.categories.get(code="JEUNE_SEVRE")
    animal.physiological_stage = ovin.stages.get(code="CROISSANCE")
    animal.registered_on = ago(100)
    animal.save()
    return animal


# --- Rappel de pesée ------------------------------------------------------------------------------


def test_weighing_reminder_is_explained(farm, complete_animal):
    Weighing.objects.create(animal=complete_animal, weight_kg=30, weighed_on=ago(35))
    evaluate_farm(farm)
    alert = open_alerts("WEIGHING_REMINDER").get()
    assert alert.rule_code == "weighing_interval"
    assert alert.trigger_data == {
        "last_weighing_on": ago(35).isoformat(),
        "reference_date": ago(35).isoformat(),
        "days_since": 35,
        "interval_days": 30,
    }
    assert "il y a 35 jours" in alert.message and alert.severity == "INFO"
    assert alert.target == complete_animal


def test_no_reminder_before_interval_and_warning_when_long_overdue(farm, complete_animal):
    Weighing.objects.create(animal=complete_animal, weight_kg=30, weighed_on=ago(10))
    evaluate_farm(farm)
    assert not open_alerts("WEIGHING_REMINDER").exists()
    Weighing.objects.all().delete()
    Weighing.objects.create(animal=complete_animal, weight_kg=30, weighed_on=ago(70))
    evaluate_farm(farm)
    assert open_alerts("WEIGHING_REMINDER").get().severity == "WARNING"


def test_reevaluation_never_duplicates_and_auto_resolves(farm, complete_animal):
    Weighing.objects.create(animal=complete_animal, weight_kg=30, weighed_on=ago(40))
    evaluate_farm(farm)
    evaluate_farm(farm)
    assert open_alerts("WEIGHING_REMINDER").count() == 1
    Weighing.objects.create(animal=complete_animal, weight_kg=32, weighed_on=TODAY)
    stats = evaluate_farm(farm)
    assert stats["resolved"] == 1
    resolved = Alert.objects.get(alert_type="WEIGHING_REMINDER")
    assert resolved.status == "RESOLVED" and resolved.trigger_data["resolution"].startswith("automatique")


def test_dismissed_alert_not_recreated_while_situation_unchanged(farm, complete_animal, breeder):
    Weighing.objects.create(animal=complete_animal, weight_kg=30, weighed_on=ago(40))
    evaluate_farm(farm)
    alert = open_alerts("WEIGHING_REMINDER").get()
    alert.status, alert.resolved_by = "DISMISSED", breeder
    alert.save()
    evaluate_farm(farm)
    assert not open_alerts("WEIGHING_REMINDER").exists()


def test_farm_rule_overrides_default_and_can_be_disabled(farm, complete_animal):
    Weighing.objects.create(animal=complete_animal, weight_kg=30, weighed_on=ago(40))
    rule = AlertRule.objects.create(
        farm=farm, alert_type="WEIGHING_REMINDER", name="Mensuel+", parameters={"interval_days": 60}
    )
    evaluate_farm(farm)
    assert not open_alerts("WEIGHING_REMINDER").exists()
    rule.parameters = {"interval_days": 30}
    rule.save()
    evaluate_farm(farm)
    assert open_alerts("WEIGHING_REMINDER").get().rule == rule
    rule.is_active = False
    rule.save()
    evaluate_farm(farm)
    assert not open_alerts("WEIGHING_REMINDER").exists()


# --- Informations manquantes -----------------------------------------------------------------


def test_missing_data_lists_fields_and_resolves_when_completed(farm, animal, ovin):
    evaluate_farm(farm)
    alert = open_alerts("MISSING_DATA").get()
    assert set(alert.trigger_data["missing_fields"]) == {
        "date de naissance ou âge estimé",
        "aucun poids enregistré",
        "catégorie",
        "stade physiologique",
    }
    animal.birth_date = ago(100)
    animal.initial_weight_kg = 20
    animal.category = ovin.categories.first()
    animal.physiological_stage = ovin.stages.first()
    animal.save()
    evaluate_farm(farm)
    assert not open_alerts("MISSING_DATA").exists()


# --- Croissance hors plage ------------------------------------------------------------------------


def test_growth_alert_only_with_validated_range_and_never_a_diagnosis(
    farm, complete_animal, ovin, validated_kwargs
):
    Weighing.objects.create(animal=complete_animal, weight_kg=20, weighed_on=ago(30))
    Weighing.objects.create(animal=complete_animal, weight_kg=21, weighed_on=TODAY)  # 33,3 g/j
    draft = GrowthMonitoringRange.objects.create(name="Brouillon", species=ovin, adg_min_g=100)
    evaluate_farm(farm)
    assert not open_alerts("GROWTH_OUT_OF_RANGE").exists()
    draft.delete()
    GrowthMonitoringRange.objects.create(
        name="Plage validée (test)", species=ovin, adg_min_g=100, adg_max_g=250, **validated_kwargs
    )
    evaluate_farm(farm)
    alert = open_alerts("GROWTH_OUT_OF_RANGE").get()
    assert alert.trigger_data["position"] == "below" and alert.trigger_data["adg_g_per_day"] == "33.3"
    assert NOT_A_DIAGNOSIS in alert.message
    assert "Source de test contrôlée" in alert.message


# --- Suivi alimentaire et formules --------------------------------------------------------------


def test_follow_up_reminder_for_ration_without_records(farm, complete_animal, ovin):
    formula = FeedFormula.objects.create(farm=farm, name="F", species=ovin, mode="MANUAL")
    ration = Ration.objects.create(
        farm=farm, name="Ration A", formula=formula, animal=complete_animal, start_date=ago(10)
    )
    evaluate_farm(farm)
    assert open_alerts("FOLLOW_UP_REMINDER").get().trigger_data["last_record_on"] is None
    FeedingRecord.objects.create(
        farm=farm, ration=ration, animal=complete_animal, quantity_distributed_kg=1, fed_on=TODAY
    )
    evaluate_farm(farm)
    assert not open_alerts("FOLLOW_UP_REMINDER").exists()


def test_formula_pending_review_alert(farm, ovin):
    FeedFormula.objects.create(
        farm=farm, name="À vérifier", species=ovin, mode="MANUAL", status="PENDING_REVIEW"
    )
    evaluate_farm(farm)
    assert "ne doit pas être considérée comme validée" in open_alerts("FORMULA_TO_REVIEW").get().message


# --- Données à valider (experts) --------------------------------------------------------------------


def test_pending_reference_data_alerts_reviewers_only(make_user, ingredient, nutrient, source):
    expert, admin, breeder = make_user("EXPERT"), make_user("ADMIN"), make_user()
    IngredientComposition.objects.create(
        ingredient=ingredient(), nutrient=nutrient("MAT"), value=100, source=source, status="PENDING"
    )
    evaluate_reviewers()
    recipients = set(open_alerts("REFERENCE_TO_VALIDATE").values_list("recipient", flat=True))
    assert recipients == {expert.pk, admin.pk}
    assert breeder.pk not in recipients
    IngredientComposition.objects.update(status="DRAFT")
    evaluate_reviewers()
    assert not open_alerts("REFERENCE_TO_VALIDATE").exists()


# --- Intégration ----------------------------------------------------------------------------------


def test_recording_a_weighing_through_api_refreshes_alerts(farm, complete_animal, breeder, client_for):
    Weighing.objects.create(animal=complete_animal, weight_kg=30, weighed_on=ago(40))
    evaluate_farm(farm)
    assert open_alerts("WEIGHING_REMINDER").exists()
    client_for(breeder).post(
        "/api/v1/weighings/", {"animal": complete_animal.pk, "weight_kg": "31"}, format="json"
    )
    assert not open_alerts("WEIGHING_REMINDER").exists()


def test_management_command(farm, animal):
    out = StringIO()
    call_command("evaluate_alerts", stdout=out)
    assert "1 exploitation(s) évaluée(s)" in out.getvalue()
    assert open_alerts("MISSING_DATA").exists()

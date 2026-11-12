"""Rations types validées (application immédiate) et délai de vérification convenu (relances)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from alerts.engine import evaluate_farm, evaluate_reviewers
from alerts.models import Alert
from animals.models import Animal, AnimalGroup
from farms.models import FarmMembership
from feeding.serializers import ration_blocker
from formulations.models import FeedFormula, RationTemplate
from growth.models import Weighing

from .test_calculate_api import request, world  # noqa: F401  (fixtures réutilisées)

pytestmark = pytest.mark.django_db
T = "/api/v1/ration-templates/"


@pytest.fixture
def nutritionist(world, make_user, client_for):  # noqa: F811
    user = make_user("EXPERT", email="nutrition@isfar.sn")
    FarmMembership.objects.create(farm=world["farm"], user=user, role="EXPERT")
    return client_for(user)


@pytest.fixture
def lot(world):  # noqa: F811
    group = AnimalGroup.objects.create(farm=world["farm"], name="Lot embouche", species=world["ovin"])
    for tag, kg in (("E-1", 34), ("E-2", 36)):
        a = Animal.objects.create(
            farm=world["farm"], species=world["ovin"], tag_number=tag, sex="M", group=group
        )
        Weighing.objects.create(animal=a, weighed_on=timezone.localdate(), weight_kg=kg)
    return group


def validated_formula(world, nutritionist):  # noqa: F811
    fid = request(world).json()["formula"]["id"]
    world["client"].post(f"/api/v1/formulas/{fid}/submit-review/")
    assert nutritionist.post(f"/api/v1/formulas/{fid}/validate/").status_code == 200
    return fid


def validated_template(world, nutritionist):  # noqa: F811
    fid = validated_formula(world, nutritionist)
    body = {"formula": fid, "name": "Embouche 30-40 kg", "weight_min_kg": "30", "weight_max_kg": "40"}
    created = nutritionist.post(f"{T}from-formula/", body, format="json")
    assert created.status_code == 201, created.json()
    tid = created.json()["id"]
    assert created.json()["status"] == "DRAFT" and len(created.json()["items"]) == 2
    validated = nutritionist.post(f"{T}{tid}/validate/", {"comment": "Conforme"}, format="json")
    assert validated.status_code == 200, validated.json()
    return tid


def test_template_applies_immediately_and_can_feed_animals(world, nutritionist, lot):  # noqa: F811
    tid = validated_template(world, nutritionist)
    farm = world["farm"]
    matching = world["client"].get(f"{T}matching/?farm={farm.pk}&group={lot.pk}").json()
    assert [t["id"] for t in matching] == [tid]
    applied = world["client"].post(f"{T}{tid}/apply/", {"farm": farm.pk, "group": lot.pk}, format="json")
    assert applied.status_code == 201, applied.json()
    # Objectif choisi par l'éleveur (identifiant) : accepté et enregistré sur la formule.
    from animals.models import ProductionObjective

    goal = ProductionObjective.objects.first()
    with_goal = world["client"].post(
        f"{T}{tid}/apply/", {"farm": farm.pk, "group": lot.pk, "objective": goal.pk}, format="json"
    )
    assert with_goal.status_code == 201, with_goal.json()  # ration type valable pour tout objectif
    assert with_goal.json()["objective"] == goal.pk
    body = applied.json()
    assert (
        body["status"] == "VALIDATED"
        and body["mode"] == "TEMPLATE"
        and body["template_name"] == "Embouche 30-40 kg"
    )
    # Mêmes proportions et même ingestion que la formule validée ; coût recalculé avec les prix du jour.
    assert body["dm_intake_kg_day"] == "1.000" and body["cost_per_day"] == "200.00"
    formula = FeedFormula.objects.get(pk=body["id"])
    assert ration_blocker(formula) is None  # une ration peut être créée sans attendre
    assert formula.result_snapshot["profile"]["head_count"] == 2


def test_template_is_never_applied_outside_its_profile(world, nutritionist, lot):  # noqa: F811
    tid = validated_template(world, nutritionist)
    heavy = Animal.objects.create(
        farm=world["farm"], species=world["ovin"], tag_number="H-1", sex="M", initial_weight_kg=55
    )
    farm = world["farm"]
    assert world["client"].get(f"{T}matching/?farm={farm.pk}&animal={heavy.pk}").json() == []
    refused = world["client"].post(f"{T}{tid}/apply/", {"farm": farm.pk, "animal": heavy.pk}, format="json")
    assert refused.status_code == 400 and "tranche de poids" in refused.json()["detail"]


def test_farmers_see_only_validated_templates_and_cannot_write_them(world, nutritionist, lot):  # noqa: F811
    validated_formula(world, nutritionist)
    fid = FeedFormula.objects.filter(status="VALIDATED").first().pk
    nutritionist.post(
        f"{T}from-formula/",
        {"formula": fid, "name": "Brouillon", "weight_min_kg": "30", "weight_max_kg": "40"},
        format="json",
    )
    assert world["client"].get(T).json()["results"] == []  # brouillon invisible pour l'éleveur
    farmer_try = world["client"].post(
        f"{T}from-formula/",
        {"formula": fid, "name": "x", "weight_min_kg": "1", "weight_max_kg": "2"},
        format="json",
    )
    assert farmer_try.status_code == 403
    draft = RationTemplate.objects.get(name="Brouillon")
    applied = world["client"].post(
        f"{T}{draft.pk}/apply/", {"farm": world["farm"].pk, "group": lot.pk}, format="json"
    )
    assert applied.status_code == 404  # non validée : n'existe pas pour l'éleveur


def test_review_deadline_escalates(world, nutritionist, make_user, settings):  # noqa: F811
    settings.FORMULA_REVIEW_DEADLINE_HOURS = 48
    admin = make_user("ADMIN", email="admin@ndeyam.sn")
    fid = request(world).json()["formula"]["id"]
    world["client"].post(f"/api/v1/formulas/{fid}/submit-review/")
    body = world["client"].get(f"/api/v1/formulas/{fid}/").json()
    assert body["review_requested_at"] and body["review_due_at"] and body["review_overdue"] is False
    farm_alert = Alert.objects.get(farm=world["farm"], alert_type="FORMULA_TO_REVIEW", status="OPEN")
    assert "Réponse attendue avant le" in farm_alert.message and farm_alert.severity == "INFO"

    FeedFormula.objects.filter(pk=fid).update(review_requested_at=timezone.now() - timedelta(hours=49))
    evaluate_farm(world["farm"])
    evaluate_reviewers()
    late = Alert.objects.get(farm=world["farm"], alert_type="FORMULA_TO_REVIEW", status="OPEN")
    assert late.severity == "CRITICAL" and late.title.startswith("Vérification en retard")
    assert world["client"].get(f"/api/v1/formulas/{fid}/").json()["review_overdue"] is True
    reminder = Alert.objects.get(recipient=admin, alert_type="FORMULA_TO_REVIEW", status="OPEN")
    assert reminder.title == "1 vérification(s) de ration en retard"

    # Décision de l'expert : les alertes de retard sont résolues automatiquement.
    nutritionist.post(f"/api/v1/formulas/{fid}/validate/")
    evaluate_reviewers()
    assert not Alert.objects.filter(alert_type="FORMULA_TO_REVIEW", status="OPEN").exists()


def test_english_messages_for_templates_and_delays(world, nutritionist, lot):  # noqa: F811
    tid = validated_template(world, nutritionist)
    heavy = Animal.objects.create(
        farm=world["farm"], species=world["ovin"], tag_number="H-2", sex="M", initial_weight_kg=60
    )
    refused = world["client"].post(
        f"{T}{tid}/apply/",
        {"farm": world["farm"].pk, "animal": heavy.pk},
        format="json",
        HTTP_ACCEPT_LANGUAGE="en",
    )
    assert refused.json()["detail"].startswith("This ration template does not match")

import pytest

from alerts.models import Alert
from conftest import rejected_by_database

pytestmark = pytest.mark.django_db


def make_alert(**kwargs):
    defaults = {
        "alert_type": "WEIGHING_REMINDER",
        "title": "Pesée à prévoir",
        "message": "Dernière pesée il y a 35 jours.",
        "rule_code": "weighing_interval",
        "trigger_data": {"days_since_last_weighing": 35, "threshold_days": 30},
        "dedup_key": "weighing:animal:1",
    }
    return Alert.objects.create(**{**defaults, **kwargs})


def test_alert_needs_a_farm_or_a_recipient():
    with rejected_by_database():
        make_alert()


def test_alert_keeps_its_explanation(farm):
    alert = make_alert(farm=farm)
    alert.refresh_from_db()
    assert alert.rule_code == "weighing_interval"
    assert alert.trigger_data["threshold_days"] == 30


def test_no_duplicate_open_alert_for_the_same_cause(farm):
    make_alert(farm=farm)
    with rejected_by_database():
        make_alert(farm=farm)


def test_new_alert_allowed_once_previous_is_resolved(farm):
    first = make_alert(farm=farm)
    first.status = "RESOLVED"
    first.save()
    make_alert(farm=farm)
    assert Alert.objects.count() == 2

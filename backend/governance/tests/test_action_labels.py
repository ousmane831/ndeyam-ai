"""Chaque action journalisée a un libellé français (défaut trouvé à l'étape 11 : codes bruts à l'écran)."""

import re
from pathlib import Path

from governance.activity import ACTION_LABELS, action_label

ROOT = Path(__file__).resolve().parents[2]
APPS = [
    "accounts",
    "alerts",
    "animals",
    "assistant",
    "core",
    "farms",
    "feeding",
    "formulations",
    "governance",
    "growth",
    "knowledge_base",
    "nutrition",
]


def _literal_actions():
    pattern = re.compile(r'log_activity\(\s*[\w.]+,\s*"([a-z_]+\.[a-z_]+)"')
    pattern_multiline = re.compile(r'log_activity\(\s*\n\s*[\w.]+,\s*\n\s*"([a-z_]+\.[a-z_]+)"')
    found = set()
    for app in APPS:
        for path in (ROOT / app).rglob("*.py"):
            if "tests" in path.parts or "migrations" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            found |= set(pattern.findall(text)) | set(pattern_multiline.findall(text))
            found |= set(
                re.findall(r'^\s*"((?:import|account|admin|farm|alert_rule)\.[a-z_]+)",\s*$', text, re.M)
            )
    return found


def _dynamic_actions():
    prefixes = set()
    for app in APPS:
        for path in (ROOT / app).rglob("views.py"):
            prefixes |= set(re.findall(r'activity_prefix = "([a-z_]+)"', path.read_text(encoding="utf-8")))
    crud = {f"{p}.{verb}" for p in prefixes for verb in ("created", "updated", "deleted")}
    return (
        crud
        | {f"validation.{n}" for n in ("submit", "validate", "reject", "revert")}
        | {f"alert.{s}" for s in ("acknowledged", "resolved", "dismissed")}
        | {f"formula.{s}" for s in ("pending_review", "validated", "rejected")}
    )


def test_every_logged_action_has_a_label():
    actions = _literal_actions() | _dynamic_actions()
    assert len(actions) > 40  # garde-fou : la recherche dans le code fonctionne
    missing = sorted(a for a in actions if a not in ACTION_LABELS)
    assert not missing, missing


def test_unknown_action_falls_back_to_its_code():
    assert action_label("inconnue.action") == "inconnue.action"
    assert action_label("alert.resolved") == "Alerte résolue"

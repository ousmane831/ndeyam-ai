"""
Point d'extension pour une future prédiction de croissance par apprentissage automatique.

AUCUN modèle n'est entraîné ni fourni dans cette version. Un modèle ne pourra être branché que
lorsque suffisamment de données réelles et représentatives (pesées sourcées, contexte d'élevage)
auront été collectées, puis évaluées. Le jeu d'apprentissage peut être constitué à partir de
l'export CSV des pesées (`GET /api/v1/weighings/export/`).

Pour brancher un modèle : implémenter `GrowthPredictor`, l'enregistrer via `register_predictor()`
au démarrage, et documenter ses données d'entraînement, ses performances et ses limites.
"""

from datetime import date
from typing import Protocol


class GrowthPredictor(Protocol):
    name: str
    version: str
    training_summary: str

    def predict_weight(self, animal, target_date: date) -> dict:
        """Doit renvoyer {"weight_kg": ..., "interval": [bas, haut], "confidence": ...}."""


_predictor: GrowthPredictor | None = None


def register_predictor(predictor: GrowthPredictor) -> None:
    global _predictor
    _predictor = predictor


def get_predictor() -> GrowthPredictor | None:
    return _predictor


def prediction_status() -> dict:
    predictor = get_predictor()
    if predictor is None:
        return {
            "available": False,
            "reason": (
                "Aucun modèle de prédiction n'est disponible : il sera développé lorsque "
                "suffisamment de données "
                "réelles et représentatives auront été collectées."
            ),
        }
    return {
        "available": True,
        "name": predictor.name,
        "version": predictor.version,
        "training_summary": predictor.training_summary,
    }

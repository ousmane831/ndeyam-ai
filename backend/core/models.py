"""
Modèles abstraits partagés par toutes les applications de NDEYAM AI.

Ils ne créent aucune table : ils factorisent les champs de traçabilité
(dates de création/modification) exigés par le cahier des charges.
"""

from django.db import models


class TimeStampedModel(models.Model):
    """Ajoute les dates de création et de dernière modification."""

    created_at = models.DateTimeField("créé le", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True

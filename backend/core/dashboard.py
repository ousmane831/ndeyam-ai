"""
Indicateurs du tableau de bord.

Toutes les valeurs sont calculées à partir des données enregistrées, sur les exploitations accessibles à
l'utilisateur (ou une seule avec `?farm=`). Aucune statistique n'est estimée ni complétée : une valeur
impossible à calculer est renvoyée vide, avec le nombre d'enregistrements sur lesquels elle repose.
"""

from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alerts.models import Alert, AlertStatus
from animals.models import Animal, AnimalGroup, AnimalStatus
from farms.access import readable_farms
from feeding.models import FeedingRecord, Ration, RationStatus
from governance.activity import action_label
from governance.models import ActivityLog
from growth.models import Weighing


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Indicateurs du tableau de bord (données réelles uniquement)",
        parameters=[OpenApiParameter("farm", int, description="Limiter à une exploitation")],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        farms = readable_farms(request.user)
        farm_id = request.query_params.get("farm")
        if farm_id:
            farms = farms.filter(pk=farm_id) if farm_id.isdigit() else farms.none()
            if not farms.exists():
                # Même règle que le reste de l'API : une exploitation inaccessible est « introuvable ».
                raise NotFound("Exploitation introuvable.")
        today = timezone.localdate()
        since_30 = today - timedelta(days=30)

        animals = Animal.objects.filter(farm__in=farms, status=AnimalStatus.ACTIVE)
        by_species = list(
            animals.values("species__code", "species__name").annotate(count=Count("id")).order_by("-count")
        )
        by_category = list(animals.values("category__name").annotate(count=Count("id")).order_by("-count"))
        by_sex = {row["sex"]: row["count"] for row in animals.values("sex").annotate(count=Count("id"))}

        weighings = Weighing.objects.filter(animal__farm__in=farms, animal__status=AnimalStatus.ACTIVE)
        latest = weighings.select_related("animal").order_by("-weighed_on", "-created_at")[:5]
        six_months_ago = (today.replace(day=1) - timedelta(days=150)).replace(day=1)
        trend = (
            weighings.filter(weighed_on__gte=six_months_ago)
            .annotate(month=TruncMonth("weighed_on"))
            .values("month")
            .annotate(
                mean_weight_kg=Avg("weight_kg"), weighings=Count("id"), animals=Count("animal", distinct=True)
            )
            .order_by("month")
        )

        active_rations = Ration.objects.filter(farm__in=farms, status=RationStatus.ACTIVE).select_related(
            "formula", "animal", "group"
        )
        records = FeedingRecord.objects.filter(farm__in=farms, fed_on__gte=since_30)
        cost = records.aggregate(total=Sum("estimated_cost"), distributed=Sum("quantity_distributed_kg"))

        open_alerts = Alert.objects.filter(
            Q(farm__in=farms) | Q(recipient=request.user),
            status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED],
        )
        activity = (
            ActivityLog.objects.filter(farm__in=farms).select_related("actor").order_by("-created_at")[:10]
        )

        return Response(
            {
                "farms_count": farms.count(),
                "animals": {
                    "total": animals.count(),
                    "by_species": [
                        {"code": r["species__code"], "name": r["species__name"], "count": r["count"]}
                        for r in by_species
                    ],
                    "by_category": [
                        {"name": r["category__name"] or "Non renseignée", "count": r["count"]}
                        for r in by_category
                    ],
                    "by_sex": {"M": by_sex.get("M", 0), "F": by_sex.get("F", 0)},
                },
                "groups_count": AnimalGroup.objects.filter(farm__in=farms, is_active=True).count(),
                "weighings": {
                    "last_30_days": weighings.filter(weighed_on__gte=since_30).count(),
                    "never_weighed": animals.filter(weighings__isnull=True).count(),
                    "latest": [
                        {
                            "id": w.pk,
                            "animal_id": w.animal_id,
                            "animal": str(w.animal),
                            "tag_number": w.animal.tag_number,
                            "animal_name": w.animal.name,
                            "weighed_on": w.weighed_on,
                            "weight_kg": str(w.weight_kg),
                        }
                        for w in latest
                    ],
                },
                "weight_trend": {
                    "points": [
                        {
                            "month": r["month"].strftime("%Y-%m"),
                            "mean_weight_kg": round(float(r["mean_weight_kg"]), 2),
                            "weighings": r["weighings"],
                            "animals": r["animals"],
                        }
                        for r in trend
                    ],
                    "note": (
                        "Moyenne des pesées de chaque mois, tous animaux confondus : les animaux pesés "
                        "changent d'un mois à l'autre, ce n'est pas la courbe d'un animal."
                    ),
                },
                "rations": {
                    "active_count": active_rations.count(),
                    "active": [
                        {
                            "id": r.pk,
                            "name": r.name,
                            "formula": r.formula.name,
                            "formula_status": r.formula.get_status_display(),
                            "target": f"Animal {r.animal}" if r.animal_id else f"Lot {r.group}",
                            "start_date": r.start_date,
                        }
                        for r in active_rations[:5]
                    ],
                },
                "feeding_cost": {
                    "period_days": 30,
                    "estimated_cost": str(cost["total"]) if cost["total"] is not None else None,
                    "distributed_kg": str(cost["distributed"]) if cost["distributed"] is not None else None,
                    "records": records.count(),
                    "records_without_cost": records.filter(estimated_cost__isnull=True).count(),
                    "currency": "XOF",
                },
                "alerts": {
                    "open": open_alerts.count(),
                    "by_severity": {
                        r["severity"]: r["n"] for r in open_alerts.values("severity").annotate(n=Count("id"))
                    },
                    "latest": [
                        {"id": a.pk, "title": a.title, "severity": a.severity, "alert_type": a.alert_type}
                        for a in open_alerts.order_by("-created_at")[:5]
                    ],
                },
                "recent_activity": [
                    {
                        "id": e.pk,
                        "action": e.action,
                        "label": action_label(e.action),
                        "object": e.object_repr,
                        # Nom affiché plutôt que l'adresse e-mail (repli sur l'e-mail si aucun nom).
                        "actor": str(e.actor) if e.actor else None,
                        "created_at": e.created_at,
                    }
                    for e in activity
                ],
            }
        )

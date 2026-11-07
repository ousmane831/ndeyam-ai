"""
Import CSV des animaux d'une exploitation.

Colonnes : numero (obligatoire) ; sexe (M/F, mâle/femelle, obligatoire) ;
espece (code, défaut OVIN) ; nom ; race ;
date_naissance (AAAA-MM-JJ ou JJ/MM/AAAA) ; age_estime_mois ; poids_initial_kg ; categorie (code ou nom) ;
stade (code ou nom) ; lot (nom ; créé s'il n'existe pas) ; observations.

Chaque ligne passe par les mêmes contrôles que la saisie manuelle (AnimalSerializer). Les numéros déjà
présents dans l'exploitation sont signalés en erreur, jamais écrasés.
"""

from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.csv_io import parse_decimal, read_csv_upload
from governance.activity import log_activity
from governance.models import ImportBatch, ImportStatus

from .models import AnimalCategory, AnimalGroup, Breed, PhysiologicalStage, Species

SEX = {"m": "M", "male": "M", "mâle": "M", "f": "F", "femelle": "F"}


def _parse_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"date_naissance : « {value} » (formats acceptés : AAAA-MM-JJ ou JJ/MM/AAAA).")


def _lookup(model, species, value, field_label):
    if not value:
        return None
    obj = model.objects.filter(Q(code__iexact=value) | Q(name__iexact=value), species=species).first()
    if obj is None:
        raise ValueError(f"{field_label} : « {value} » inconnu pour l'espèce {species.name}.")
    return obj.pk


def _row_payload(row, farm):
    species_code = row.get("espece") or "OVIN"
    species = Species.objects.filter(code__iexact=species_code).first()
    if species is None:
        raise ValueError(f"espece : code « {species_code} » inconnu.")
    sex = SEX.get((row.get("sexe") or "").strip().lower())
    if sex is None:
        raise ValueError("sexe : M ou F attendu.")
    payload = {
        "farm": farm.pk,
        "tag_number": row.get("numero", ""),
        "name": row.get("nom", ""),
        "species": species.pk,
        "sex": sex,
        "observations": row.get("observations", ""),
    }
    if row.get("race"):
        breed = Breed.objects.filter(species=species, name__iexact=row["race"]).first()
        if breed is None:
            raise ValueError(f"race : « {row['race']} » inconnue pour l'espèce {species.name}.")
        payload["breed"] = breed.pk
    birth = _parse_date(row.get("date_naissance"))
    if birth:
        payload["birth_date"] = birth.isoformat()
    age = parse_decimal(row.get("age_estime_mois"), "age_estime_mois")
    if age is not None:
        payload["estimated_age_months"] = str(age)
    weight = parse_decimal(row.get("poids_initial_kg"), "poids_initial_kg")
    if weight is not None:
        payload["initial_weight_kg"] = str(weight)
    payload["category"] = _lookup(AnimalCategory, species, row.get("categorie"), "categorie")
    payload["physiological_stage"] = _lookup(PhysiologicalStage, species, row.get("stade"), "stade")
    if row.get("lot"):
        group, _ = AnimalGroup.objects.get_or_create(
            farm=farm, name=row["lot"], defaults={"species": species}
        )
        payload["group"] = group.pk
    return {k: v for k, v in payload.items() if v is not None}


def import_animals(upload, farm, request):
    from .serializers import AnimalSerializer

    rows, sha = read_csv_upload(upload, ["numero", "sexe"])
    batch = ImportBatch.objects.create(
        kind="animals",
        file_name=getattr(upload, "name", "import.csv"),
        file_sha256=sha,
        imported_by=request.user,
        total_rows=len(rows),
        is_demo=farm.is_demo,
    )
    errors = []
    for index, row in enumerate(rows, start=2):
        try:
            with transaction.atomic():
                serializer = AnimalSerializer(data=_row_payload(row, farm), context={"request": request})
                if not serializer.is_valid():
                    messages = "; ".join(
                        f"{field} : {' '.join(map(str, msgs))}" for field, msgs in serializer.errors.items()
                    )
                    raise ValueError(messages)
                serializer.save(created_by=request.user, is_demo=farm.is_demo)
                batch.created_rows += 1
        except ValueError as exc:
            errors.append({"line": index, "error": str(exc)})
    batch.error_rows = len(errors)
    batch.errors = errors[:500]
    batch.status = ImportStatus.COMPLETED_WITH_ERRORS if errors else ImportStatus.COMPLETED
    batch.finished_at = timezone.now()
    batch.save()
    log_activity(
        request,
        "import.animals",
        batch,
        farm=farm,
        details={"created": batch.created_rows, "errors": batch.error_rows},
    )
    return batch

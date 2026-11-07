"""
Import CSV des compositions nutritionnelles (experts et administrateurs).

Colonnes : ingredient ; categorie (code, obligatoire si l'ingrédient est nouveau) ; nutriment (code) ;
systeme (code, vide pour un nutriment universel) ; valeur ; date_reference (AAAA-MM-JJ, facultatif) ;
methode (facultatif) ; origine (facultatif).

Règles :
- la source est choisie pour tout le fichier et obligatoire ;
- tout ce qui est importé est en BROUILLON : aucune donnée n'est validée par un import ;
- une valeur déjà VALIDÉE n'est jamais modifiée par un import (ligne signalée en erreur) ;
- une cellule « valeur » vide est ignorée : une composition inconnue reste inconnue (jamais zéro).
"""

from datetime import date

from django.db import transaction
from django.utils import timezone

from core.csv_io import parse_decimal, read_csv_upload
from governance.activity import log_activity
from governance.models import ImportBatch, ImportStatus, ValidationStatus

from .models import Ingredient, IngredientCategory, IngredientComposition, Nutrient

REQUIRED = ["ingredient", "nutriment", "valeur"]


def _row_to_composition(row, source, is_demo, user, cache):
    name = row.get("ingredient", "")
    if not name:
        raise ValueError("ingredient : nom manquant.")
    value = parse_decimal(row.get("valeur"), "valeur")
    if value is None:
        return "skipped"
    if value < 0:
        raise ValueError("valeur : une teneur ne peut pas être négative.")

    system_code = (row.get("systeme") or "").upper() or None
    nutrient_code = (row.get("nutriment") or "").upper()
    key = (nutrient_code, system_code)
    if key not in cache:
        cache[key] = (
            Nutrient.objects.filter(code__iexact=nutrient_code, system__code__iexact=system_code).first()
            if system_code
            else Nutrient.objects.filter(code__iexact=nutrient_code, system=None).first()
        )
    nutrient = cache[key]
    if nutrient is None:
        label = f"{nutrient_code} ({system_code})" if system_code else nutrient_code
        raise ValueError(f"nutriment : « {label} » inconnu. Vérifiez le code et le système.")
    if nutrient.category == "DRY_MATTER" and not (0 < value <= 1000):
        raise ValueError("valeur : la matière sèche doit être comprise entre 0 et 1000 g/kg brut.")

    ingredient = Ingredient.objects.filter(name__iexact=name, farm=None).first()
    created_ingredient = False
    if ingredient is None:
        category = IngredientCategory.objects.filter(code__iexact=row.get("categorie", "")).first()
        if category is None:
            raise ValueError("categorie : code obligatoire et valide pour un nouvel ingrédient.")
        ingredient = Ingredient.objects.create(
            name=name, category=category, source=source, is_demo=is_demo, created_by=user
        )
        created_ingredient = True
    elif ingredient.is_demo != is_demo:
        raise ValueError("ingredient : statut DEMO différent de celui de l'import ; mélange interdit.")

    reference_date = None
    if row.get("date_reference"):
        try:
            reference_date = date.fromisoformat(row["date_reference"])
        except ValueError as exc:
            raise ValueError("date_reference : format attendu AAAA-MM-JJ.") from exc

    existing = IngredientComposition.objects.filter(
        ingredient=ingredient, nutrient=nutrient, source=source
    ).first()
    if existing and existing.status == ValidationStatus.VALIDATED:
        if existing.value == value:
            return "unchanged"
        raise ValueError(
            "valeur déjà VALIDÉE pour cette source : modification à faire manuellement par un expert."
        )
    fields = {
        "value": value,
        "reference_date": reference_date,
        "analysis_method": row.get("methode", ""),
        "sample_origin": row.get("origine", ""),
        "is_demo": is_demo,
        "status": ValidationStatus.DRAFT,
    }
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.save()
        return "updated"
    IngredientComposition.objects.create(
        ingredient=ingredient, nutrient=nutrient, source=source, created_by=user, **fields
    )
    return "created" if not created_ingredient else "created"


def import_compositions(upload, source, is_demo, user, request=None):
    rows, sha = read_csv_upload(upload, REQUIRED)
    batch = ImportBatch.objects.create(
        kind="compositions",
        file_name=getattr(upload, "name", "import.csv"),
        file_sha256=sha,
        is_demo=is_demo,
        imported_by=user,
        total_rows=len(rows),
    )
    if source.is_demo and not is_demo:
        batch.status = ImportStatus.FAILED
        batch.errors = [{"line": None, "error": "Une source DEMO ne peut alimenter que des données DEMO."}]
        batch.finished_at = timezone.now()
        batch.save()
        return batch

    errors, cache = [], {}
    for index, row in enumerate(rows, start=2):  # ligne 1 = en-têtes
        try:
            with transaction.atomic():
                outcome = _row_to_composition(row, source, is_demo, user, cache)
        except ValueError as exc:
            errors.append({"line": index, "error": str(exc)})
            continue
        if outcome == "created":
            batch.created_rows += 1
        elif outcome == "updated":
            batch.updated_rows += 1

    batch.error_rows = len(errors)
    batch.errors = errors[:500]
    batch.status = ImportStatus.COMPLETED_WITH_ERRORS if errors else ImportStatus.COMPLETED
    batch.finished_at = timezone.now()
    batch.save()
    log_activity(
        request,
        "import.compositions",
        batch,
        actor=user,
        details={"created": batch.created_rows, "updated": batch.updated_rows, "errors": batch.error_rows},
    )
    return batch

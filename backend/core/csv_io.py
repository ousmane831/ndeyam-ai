"""
Import / export CSV.

- Export : séparateur « ; » et encodage UTF-8 avec BOM, pour une ouverture directe dans Excel
  (paramètres français).
- Import : détection automatique du séparateur (« ; » ou « , ») et de l'encodage
  (UTF-8, avec ou sans BOM, sinon cp1252).
  Les nombres acceptent la virgule décimale. Chaque ligne en erreur est rapportée avec son numéro.
"""

import csv
import hashlib
import io
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 20_000


class CsvImportError(ValueError):
    pass


def _resolve(obj, path):
    for part in path.split("."):
        if obj is None:
            return ""
        obj = getattr(obj, part)
        if callable(obj):
            obj = obj()
    if obj is None:
        return ""
    if isinstance(obj, bool):
        return "oui" if obj else "non"
    if isinstance(obj, Decimal):
        return format(obj.normalize(), "f").replace(".", ",")
    return obj


def csv_response(filename, columns, rows):
    """`columns` : liste de (chemin d'attribut, en-tête)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow([header for _, header in columns])
    for row in rows:
        writer.writerow([_resolve(row, path) for path, _ in columns])
    response = HttpResponse("﻿" + buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def read_csv_upload(upload, required_columns):
    """Retourne (lignes sous forme de dict avec en-têtes normalisés, empreinte SHA-256)."""
    if upload is None:
        raise CsvImportError("Aucun fichier reçu (champ « file »).")
    raw = upload.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise CsvImportError("Fichier trop volumineux (5 Mo maximum).")
    if not raw.strip():
        raise CsvImportError("Le fichier est vide.")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    first_line = text.splitlines()[0] if text else ""
    delimiter = ";" if first_line.count(";") >= first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in required_columns if c not in headers]
    if missing:
        raise CsvImportError(f"Colonnes obligatoires absentes : {', '.join(missing)}.")
    rows = []
    for row in reader:
        rows.append({(k or "").strip().lower(): (v or "").strip() for k, v in row.items() if k is not None})
        if len(rows) > MAX_IMPORT_ROWS:
            raise CsvImportError(f"Trop de lignes ({MAX_IMPORT_ROWS} maximum).")
    return rows, hashlib.sha256(raw).hexdigest()


def parse_decimal(value, field):
    if value in ("", None):
        return None
    try:
        return Decimal(value.replace(" ", "").replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"{field} : « {value} » n'est pas un nombre valide.") from exc


def parse_bool(value):
    return str(value).strip().lower() in {"1", "oui", "o", "yes", "y", "true", "vrai", "x"}

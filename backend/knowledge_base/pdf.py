"""Extraction du texte d'un PDF (pypdf). Pas d'OCR : un PDF scanné est signalé, jamais « deviné »."""

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PAGES = 1000


class PdfExtractionError(ValueError):
    pass


def extract_pages(data: bytes) -> list[str]:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise PdfExtractionError("Le PDF est protégé par un mot de passe.") from exc
        if len(reader.pages) > MAX_PAGES:
            raise PdfExtractionError(f"Document trop long ({len(reader.pages)} pages ; {MAX_PAGES} maximum).")
        pages = [(page.extract_text() or "") for page in reader.pages]
    except PdfReadError as exc:
        raise PdfExtractionError("Fichier PDF illisible ou endommagé.") from exc
    if not any(p.strip() for p in pages):
        raise PdfExtractionError(
            "Aucun texte n'a pu être extrait : le document est probablement scanné (image). "
            "La reconnaissance de caractères (OCR) n'est pas prise en charge dans cette version."
        )
    return pages

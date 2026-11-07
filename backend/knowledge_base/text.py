"""
Traitement du texte : normalisation et découpage en passages (fonctions pures).

Découpage : passages d'environ `target` caractères, coupés de préférence en fin de paragraphe
puis de phrase, avec un chevauchement pour ne pas perdre le contexte d'une coupure.
Chaque passage conserve ses pages de début et de fin, pour citer précisément la source.
"""

import re
import unicodedata
from dataclasses import dataclass

DEFAULT_TARGET = 1200
DEFAULT_OVERLAP = 200
MIN_CHUNK = 80


def strip_accents(text: str) -> str:
    """« Matière sèche » → « Matiere seche » (recherche insensible aux accents)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def clean_page_text(text: str) -> str:
    text = text.replace("­", "")  # césures invisibles
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # mots coupés en fin de ligne
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    page_start: int
    page_end: int


def _cut_position(text: str, start: int, target: int) -> int:
    end = min(len(text), start + target)
    if end >= len(text):
        return len(text)
    window = text[start:end]
    for pattern in ("\n\n", ". ", "; ", "\n", " "):
        pos = window.rfind(pattern)
        if pos > target * 0.5:
            return start + pos + len(pattern)
    return end


def chunk_pages(
    pages: list[str], target: int = DEFAULT_TARGET, overlap: int = DEFAULT_OVERLAP
) -> list[Chunk]:
    """`pages` : texte de chaque page (index 0 = page 1)."""
    if overlap >= target:
        raise ValueError("Le chevauchement doit être inférieur à la taille des passages.")
    full, offsets = [], []  # offsets[i] = position de début de la page i dans le texte complet
    position = 0
    for page in pages:
        offsets.append(position)
        cleaned = clean_page_text(page)
        full.append(cleaned)
        position += len(cleaned) + 2
    text = "\n\n".join(full)

    def page_of(pos: int) -> int:
        page = 1
        for i, offset in enumerate(offsets):
            if offset <= pos:
                page = i + 1
        return page

    chunks, start = [], 0
    while start < len(text):
        # Commencer sur du texte réel : sinon un passage débutant par un saut de page serait
        # attribué à la page précédente (citation fausse).
        while start < len(text) and text[start].isspace():
            start += 1
        if start >= len(text):
            break
        end = _cut_position(text, start, target)
        piece = text[start:end].strip()
        if len(piece) >= MIN_CHUNK or (piece and not chunks):
            chunks.append(Chunk(len(chunks), piece, page_of(start), page_of(max(start, end - 1))))
        elif piece and chunks:
            last = chunks[-1]
            chunks[-1] = Chunk(
                last.index, f"{last.text} {piece}", last.page_start, page_of(max(start, end - 1))
            )
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
        # Reprendre au début d'un mot pour ne pas couper le chevauchement en plein mot.
        while start < len(text) and start > 0 and not text[start - 1].isspace():
            start += 1
    return chunks

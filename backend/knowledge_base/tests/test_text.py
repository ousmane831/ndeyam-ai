import pytest

from knowledge_base.text import chunk_pages, clean_page_text, strip_accents


def test_strip_accents():
    assert strip_accents("Matière sèche, Thiès, maïs") == "Matiere seche, Thies, mais"


def test_clean_page_text_rejoins_hyphenated_words():
    assert clean_page_text("ali-\nmentation   des  ovins") == "alimentation des ovins"


def test_short_document_gives_one_chunk_with_its_page():
    chunks = chunk_pages(["Texte court de test."])
    assert len(chunks) == 1 and chunks[0].page_start == chunks[0].page_end == 1


def test_long_text_is_split_with_overlap_and_page_tracking():
    sentence = "Ceci est une phrase de test pour le découpage en passages. "
    pages = [sentence * 30, sentence * 30]
    chunks = chunk_pages(pages, target=500, overlap=100)
    assert len(chunks) > 4
    assert all(len(c.text) <= 520 for c in chunks)
    assert chunks[0].page_start == 1 and chunks[-1].page_end == 2
    assert any(c.page_start == 1 and c.page_end == 2 for c in chunks)  # passage à cheval sur deux pages
    # Chevauchement : le début d'un passage reprend la fin du précédent.
    assert chunks[1].text[:30] in chunks[0].text
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunks_end_on_sentence_boundaries_when_possible():
    chunks = chunk_pages(["Première phrase de test assez longue pour remplir. " * 40], target=400, overlap=50)
    assert all(c.text.endswith(".") for c in chunks[:-1])


def test_empty_pages_are_ignored_but_page_numbers_kept():
    chunks = chunk_pages(["", "Contenu de la deuxième page pour le test du numéro de page."])
    assert chunks[0].page_start == 2


def test_overlap_must_be_smaller_than_target():
    with pytest.raises(ValueError):
        chunk_pages(["x"], target=100, overlap=100)

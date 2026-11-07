import pytest
from django.core.files.base import ContentFile

from conftest import rejected_by_database
from knowledge_base.models import DocumentChunk, TechnicalDocument

pytestmark = pytest.mark.django_db


@pytest.fixture
def document(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    doc = TechnicalDocument(title="Guide technique", file_sha256="a" * 64)
    doc.file.save("guide.pdf", ContentFile(b"%PDF-1.4 test"), save=False)
    doc.save()
    return doc


def test_new_document_is_not_usable_until_validated(document):
    assert document.status == "DRAFT"
    assert not TechnicalDocument.objects.usable_for_engine().exists()


def test_same_file_cannot_be_imported_twice(document):
    with rejected_by_database():
        TechnicalDocument.objects.create(title="Copie", file="documents/x.pdf", file_sha256="a" * 64)


def test_chunk_stores_embedding_as_float_array(document):
    chunk = DocumentChunk.objects.create(
        document=document, chunk_index=0, text="Passage", embedding=[0.1, 0.2, 0.3]
    )
    chunk.refresh_from_db()
    assert chunk.embedding == pytest.approx([0.1, 0.2, 0.3])


def test_chunk_index_unique_per_document(document):
    DocumentChunk.objects.create(document=document, chunk_index=0, text="A")
    with rejected_by_database():
        DocumentChunk.objects.create(document=document, chunk_index=0, text="B")

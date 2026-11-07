"""Base documentaire : import, indexation, validation, permissions, recherche (contenus de TEST)."""

import io

import httpx
import pytest
from django.test import override_settings

from governance.models import SourceDocument
from knowledge_base.embeddings import OllamaEmbeddings, OpenAICompatibleEmbeddings, get_embedding_provider
from knowledge_base.models import DocumentChunk, TechnicalDocument
from knowledge_base.search import search
from knowledge_base.vector_store import NumpyVectorStore, PgVectorStore, VectorStoreError

from .pdfgen import make_pdf

pytestmark = pytest.mark.django_db
URL = "/api/v1/documents/"

PAGE_1 = (
    "Guide de test.\nLes fourrages grossiers et la matière sèche des rations ovines.\n"
    "Le foin de brousse est un fourrage."
)
PAGE_2 = (
    "Chapitre deux du test.\nLe tourteau d'arachide est une source de protéines.\n"
    "Les tourteaux se conservent au sec."
)


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def pdf_file(pages=(PAGE_1, PAGE_2), name="guide.pdf"):
    f = io.BytesIO(make_pdf(list(pages)))
    f.name = name
    return f


@pytest.fixture
def real_source():
    return SourceDocument.objects.create(title="Guide technique de test", source_type="REPORT")


def upload(client, **kw):
    data = {"file": pdf_file(), "title": "Guide d'alimentation (test)", **kw}
    return client.post(URL, data, format="multipart")


# --- Import et indexation ----------------------------------------------------------------------


def test_expert_imports_pdf_which_is_indexed_but_not_validated(client_for, expert):
    response = upload(client_for(expert))
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["processing_status"] == "INDEXED" and body["status"] == "DRAFT"
    assert body["page_count"] == 2 and body["chunks_count"] >= 1
    assert "plein texte uniquement" in body["warnings"][0]  # aucun fournisseur d'embeddings en test
    chunk = DocumentChunk.objects.first()
    assert chunk.search_vector is not None and chunk.page_start == 1


def test_duplicate_file_rejected(client_for, expert):
    client = client_for(expert)
    upload(client)
    response = upload(client)
    assert response.status_code == 400 and response.json()["code"] == "duplicate_document"


def test_non_pdf_rejected(client_for, expert):
    fake = io.BytesIO(b"pas un pdf")
    fake.name = "notes.pdf"
    response = client_for(expert).post(URL, {"file": fake, "title": "X"}, format="multipart")
    assert response.status_code == 400 and "PDF" in response.json()["detail"]


def test_scanned_pdf_without_text_is_marked_failed(client_for, expert):
    response = client_for(expert).post(
        URL, {"file": pdf_file(pages=("", "")), "title": "Scan"}, format="multipart"
    )
    body = response.json()
    assert body["processing_status"] == "FAILED" and "OCR" in body["processing_error"]
    assert body["chunks_count"] == 0


def test_breeder_cannot_import(client_for, breeder):
    assert upload(client_for(breeder)).status_code == 403


# --- Validation et visibilité -------------------------------------------------------------------


def test_document_needs_source_and_indexing_to_be_validated(client_for, expert, real_source):
    client = client_for(expert)
    doc_id = upload(client).json()["id"]
    assert client.post(f"{URL}{doc_id}/validate/").status_code == 400  # pas de source
    client.patch(f"{URL}{doc_id}/", {"source": real_source.pk}, format="json")
    assert client.post(f"{URL}{doc_id}/validate/").json()["status"] == "VALIDATED"
    failed_id = client.post(
        URL, {"file": pdf_file(("", "")), "title": "Scan", "source": real_source.pk}, format="multipart"
    ).json()["id"]
    response = client.post(f"{URL}{failed_id}/validate/")
    assert response.status_code == 400 and "indexé" in response.json()["detail"]


def test_breeders_only_see_validated_documents(client_for, expert, breeder, real_source):
    client = client_for(expert)
    validated = upload(client, source=real_source.pk).json()["id"]
    client.post(f"{URL}{validated}/validate/")
    client.post(
        URL,
        {"file": pdf_file(("Brouillon de test sur le fourrage.",), "b.pdf"), "title": "Brouillon"},
        format="multipart",
    )
    visible = [d["id"] for d in client_for(breeder).get(URL).json()["results"]]
    assert visible == [validated]
    assert client_for(expert).get(URL).json()["count"] == 2


def test_demo_source_requires_demo_document(client_for, expert):
    demo = SourceDocument.objects.create(title="Fictive", source_type="OTHER", is_demo=True)
    assert upload(client_for(expert), source=demo.pk).status_code == 400


def test_download_requires_visibility(client_for, expert, breeder):
    doc_id = upload(client_for(expert)).json()["id"]
    assert client_for(expert).get(f"{URL}{doc_id}/file/").status_code == 200
    assert client_for(breeder).get(f"{URL}{doc_id}/file/").status_code == 404  # brouillon invisible


# --- Recherche plein texte --------------------------------------------------------------------


@pytest.fixture
def validated_doc(client_for, expert, real_source):
    client = client_for(expert)
    doc_id = upload(client, source=real_source.pk).json()["id"]
    client.post(f"{URL}{doc_id}/validate/")
    return doc_id


def test_full_text_search_is_french_and_accent_insensitive(client_for, breeder, validated_doc):
    client = client_for(breeder)
    for query in ("matiere seche", "fourrage", "tourteaux arachide"):
        body = client.get(f"{URL}search/", {"q": query}).json()
        assert body["method"] == "plein_texte" and body["results"], query
    hit = client.get(f"{URL}search/", {"q": "tourteau protéines"}).json()["results"][0]
    assert hit["pages"] in ("p. 2", "p. 1-2")
    assert hit["citation"].startswith("Guide d'alimentation (test), p.")
    assert "Guide technique de test" in hit["citation"]


def test_search_ignores_unvalidated_documents_by_default(client_for, expert, breeder):
    upload(client_for(expert))  # brouillon
    assert client_for(breeder).get(f"{URL}search/", {"q": "fourrage"}).json()["results"] == []
    preview = client_for(expert).get(f"{URL}search/", {"q": "fourrage", "include_unvalidated": "true"}).json()
    assert preview["results"]
    # un éleveur ne peut pas forcer l'inclusion des brouillons
    assert (
        client_for(breeder)
        .get(f"{URL}search/", {"q": "fourrage", "include_unvalidated": "true"})
        .json()["results"]
        == []
    )


def test_search_with_no_match_says_so(client_for, breeder, validated_doc):
    body = client_for(breeder).get(f"{URL}search/", {"q": "photosynthèse"}).json()
    assert body["results"] == [] and "Aucun passage" in body["warnings"][0]


# --- Embeddings et stockage vectoriel ---------------------------------------------------------


class FakeProvider:
    """Embedding déterministe de TEST : présence de mots-clés (pas un vrai modèle)."""

    model_id = "test:mots-cles"
    KEYWORDS = ["fourrage", "foin", "tourteau", "proteine"]

    def embed(self, texts):
        from knowledge_base.text import strip_accents

        return [[float(strip_accents(t.lower()).count(k)) + 0.01 for k in self.KEYWORDS] for t in texts]


def test_semantic_search_uses_embeddings_when_available(expert, real_source):
    from knowledge_base.ingestion import process_document

    doc = TechnicalDocument.objects.create(title="Doc", file_sha256="f" * 64, source=real_source)
    data = make_pdf([PAGE_1 + "\n" * 2 + "remplissage " * 120, PAGE_2 + "\n" * 2 + "remplissage " * 120])
    process_document(doc, data, provider=FakeProvider())
    doc.refresh_from_db()
    assert doc.embedding_model == "test:mots-cles"
    assert all(c.embedding for c in doc.chunks.all())
    result = search("tourteau protéines", include_unvalidated=True, provider=FakeProvider())
    assert result["method"] == "semantique"
    assert "tourteau" in result["results"][0]["excerpt"].lower()


def test_embedding_failure_falls_back_to_full_text(expert, real_source):
    from knowledge_base.embeddings import EmbeddingError
    from knowledge_base.ingestion import process_document

    class Broken:
        model_id = "x"

        def embed(self, texts):
            raise EmbeddingError("serveur indisponible")

    doc = TechnicalDocument.objects.create(title="Doc", file_sha256="e" * 64, source=real_source)
    warnings = process_document(doc, make_pdf([PAGE_1]), provider=Broken())
    doc.refresh_from_db()
    assert doc.processing_status == "INDEXED" and doc.embedding_model == ""
    assert "plein texte uniquement" in warnings[0]
    result = search("fourrage", include_unvalidated=True, provider=Broken())
    assert result["method"] == "plein_texte" and result["results"]
    assert "indisponible" in result["warnings"][0]


def test_numpy_vector_store_ranks_by_cosine(expert):
    doc = TechnicalDocument.objects.create(title="Doc", file_sha256="d" * 64)
    for i, vec in enumerate(([1, 0], [0, 1], [0.7, 0.7])):
        DocumentChunk.objects.create(
            document=doc, chunk_index=i, text=str(i), embedding=vec, embedding_model="m"
        )
    hits = NumpyVectorStore().search([1, 0.1], DocumentChunk.objects.all(), "m", k=2)
    assert [DocumentChunk.objects.get(pk=h[0]).chunk_index for h in hits] == [0, 2]
    with pytest.raises(VectorStoreError):
        NumpyVectorStore().search([1, 0, 0], DocumentChunk.objects.all(), "m")
    with pytest.raises(VectorStoreError):
        PgVectorStore().search()


def test_openai_compatible_and_ollama_request_formats():
    seen = []

    def handler(request):
        seen.append((str(request.url), request.headers.get("authorization"), request.content))
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(
                200, json={"data": [{"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]}]}
            )
        return httpx.Response(200, json={"embeddings": [[1.0], [2.0]]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    oa = OpenAICompatibleEmbeddings(
        model="m", api_key="cle-test", base_url="https://api.exemple/v1/", client=client
    )
    assert oa.embed(["a", "b"]) == [[1.0], [2.0]]  # remis dans l'ordre des index
    assert seen[0][0] == "https://api.exemple/v1/embeddings" and seen[0][1] == "Bearer cle-test"
    ol = OllamaEmbeddings(model="m", base_url="http://localhost:11434", client=client)
    assert ol.embed(["a", "b"]) == [[1.0], [2.0]]
    assert seen[1][0] == "http://localhost:11434/api/embed" and seen[1][1] is None


def test_provider_configuration_is_checked():
    assert get_embedding_provider() is None  # tests : aucun fournisseur
    cfg = {"PROVIDER": "openai_compatible", "MODEL": "m", "API_KEY": "", "BASE_URL": "https://x"}
    with override_settings(EMBEDDINGS=cfg):
        assert get_embedding_provider() is None  # clé manquante
    with override_settings(EMBEDDINGS={**cfg, "API_KEY": "k"}):
        assert isinstance(get_embedding_provider(), OpenAICompatibleEmbeddings)


def test_status_endpoint_never_exposes_keys(client_for, breeder):
    with override_settings(
        EMBEDDINGS={
            "PROVIDER": "openai_compatible",
            "MODEL": "m",
            "API_KEY": "secret-123",
            "BASE_URL": "https://x",
        }
    ):
        raw = client_for(breeder).get(f"{URL}status/").content.decode()
    assert "secret-123" not in raw and '"embeddings_configured":true' in raw


def test_reindex_after_configuration_change(client_for, expert, monkeypatch):
    doc_id = upload(client_for(expert)).json()["id"]
    monkeypatch.setattr("knowledge_base.ingestion.get_embedding_provider", lambda: FakeProvider())
    body = client_for(expert).post(f"{URL}{doc_id}/reindex/").json()
    assert body["embedding_model"] == "test:mots-cles" and body["embedded_chunks"] == body["chunks_count"]

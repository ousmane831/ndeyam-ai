"""Nouvelles tentatives vers les fournisseurs d'IA (quotas et surcharges des offres gratuites)."""

import httpx
import pytest

from core.http_retry import post_with_retry


def _client(statuses):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(statuses[min(len(calls), len(statuses)) - 1], json={"ok": True})

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


@pytest.mark.parametrize("first", [403, 429, 503])
def test_transient_error_is_retried_until_success(first):
    client, calls = _client([first, first, 200])
    assert post_with_retry(client, "http://ia/x", json={}).status_code == 200
    assert len(calls) == 3


def test_gives_up_after_two_retries():
    client, calls = _client([429])
    assert post_with_retry(client, "http://ia/x", json={}).status_code == 429
    assert len(calls) == 3


@pytest.mark.parametrize("status", [200, 400, 401])
def test_success_and_definitive_errors_are_not_retried(status):
    client, calls = _client([status])
    assert post_with_retry(client, "http://ia/x", json={}).status_code == status
    assert len(calls) == 1


def test_llm_and_embeddings_retry_rate_limits():
    from assistant.llm import OpenAICompatibleProvider
    from knowledge_base.embeddings import OpenAICompatibleEmbeddings

    answers = iter([429, 200, 429, 200])

    def handler(request):
        status = next(answers)
        if status != 200:
            return httpx.Response(status)
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0]}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "Bonjour"}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    llm = OpenAICompatibleProvider("m", api_key="k", base_url="http://ia", client=client)
    assert llm.run("sys", [{"role": "user", "content": "Q"}], [], lambda n, a: ("", True)).text == "Bonjour"
    emb = OpenAICompatibleEmbeddings(model="m", api_key="k", base_url="http://ia", client=client)
    assert emb.embed(["mouton"]) == [[1.0]]

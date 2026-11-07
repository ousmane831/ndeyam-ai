import json
from types import SimpleNamespace

import httpx
import pytest
from django.test import override_settings

from assistant import orchestrator
from assistant.llm import (
    AnthropicProvider,
    LLMError,
    LLMProvider,
    LLMResult,
    OllamaProvider,
    OpenAICompatibleProvider,
    ToolSpec,
    configuration_problem,
    get_llm_provider,
)
from assistant.models import AIConversation, AIMessage
from assistant.tools import TOOL_SPECS, ToolContext

URL = "/api/v1/assistant/conversations/"
LLM_BASE = {
    "PROVIDER": "none",
    "MODEL": "",
    "API_KEY": "",
    "BASE_URL": "",
    "TIMEOUT_SECONDS": 5,
    "FALLBACKS": True,
}


class ScriptedProvider(LLMProvider):
    """Fournisseur factice : appelle les outils demandés puis renvoie leurs résultats comme texte."""

    name = "fake"

    def __init__(self, calls=(), error=None):
        super().__init__("fake-model")
        self.calls, self.error, self.seen = list(calls), error, {}

    def _run(self, system, history, tools, execute_tool, max_rounds):
        self.seen = {"system": system, "history": history, "tools": [t.name for t in tools]}
        if self.error:
            raise self.error
        done, outputs = [], []
        for name, args in self.calls:
            output, ok = execute_tool(name, args)
            done.append({"name": name, "input": args, "ok": ok})
            outputs.append(output)
        return LLMResult(" | ".join(outputs) or "Bonjour", done, 10, 5, "end_turn")


@pytest.fixture
def conversation(breeder, farm):
    return AIConversation.objects.create(user=breeder, farm=farm)


# --- Configuration ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "config, expected",
    [
        ({}, "LLM_PROVIDER=none"),
        ({"PROVIDER": "inconnu"}, "inconnu"),
        ({"PROVIDER": "anthropic"}, "LLM_API_KEY"),
        ({"PROVIDER": "openai_compatible", "API_KEY": "k"}, "LLM_BASE_URL"),
        ({"PROVIDER": "ollama", "BASE_URL": "http://localhost:11434"}, "LLM_MODEL"),
    ],
)
def test_configuration_problems(config, expected):
    assert expected in configuration_problem({**LLM_BASE, **config})


def test_valid_configurations():
    assert configuration_problem({**LLM_BASE, "PROVIDER": "anthropic", "API_KEY": "k"}) is None
    assert (
        configuration_problem({**LLM_BASE, "PROVIDER": "ollama", "BASE_URL": "http://x", "MODEL": "m"})
        is None
    )


def test_anthropic_defaults_to_opus_with_fallbacks():
    with override_settings(LLM={**LLM_BASE, "PROVIDER": "anthropic", "API_KEY": "k"}):
        provider = get_llm_provider(client=object())
    assert isinstance(provider, AnthropicProvider)
    assert provider.model == "claude-opus-5-5"
    assert provider.use_fallbacks is True


def test_no_provider_when_not_configured():
    assert get_llm_provider() is None


# --- API -------------------------------------------------------------------------------


def test_status_never_exposes_key(client_for, breeder):
    api = client_for(breeder)
    data = api.get(f"{URL}status/").json()
    assert data["configured"] is False
    with override_settings(LLM={**LLM_BASE, "PROVIDER": "anthropic", "API_KEY": "sk-secret"}):
        response = api.get(f"{URL}status/")
    assert response.json()["configured"] is True
    assert "sk-secret" not in response.content.decode()


def test_requires_authentication(api):
    assert api.get(URL).status_code == 401


def test_not_configured_answer_is_explicit(client_for, breeder, farm):
    api = client_for(breeder)
    conv = api.post(URL, {"farm": farm.pk}, format="json").json()
    response = api.post(f"{URL}{conv['id']}/messages/", {"content": "Combien pèse SN-001 ?"}, format="json")
    assert response.status_code == 503
    question, reply = response.json()
    assert question["role"] == "USER"
    assert reply["error_code"] == "not_configured"
    assert "n'est pas configuré" in reply["content"]
    assert api.get(f"{URL}{conv['id']}/").json()["title"] == "Combien pèse SN-001 ?"


def test_answer_with_provider(client_for, breeder, conversation, monkeypatch):
    provider = ScriptedProvider([("list_my_farms", {})])
    monkeypatch.setattr(orchestrator, "get_llm_provider", lambda: provider)
    api = client_for(breeder)
    response = api.post(f"{URL}{conversation.pk}/messages/", {"content": "Mes fermes ?"}, format="json")
    assert response.status_code == 201
    reply = response.json()[1]
    assert reply["role"] == "ASSISTANT" and reply["provider"] == "fake"
    assert reply["tool_calls"] == [{"name": "list_my_farms", "input": {}, "ok": True}]
    types = [p["type"] for p in reply["provenance"]]
    assert types == ["database", "llm"]
    assert "ne calcules jamais" in provider.seen["system"]
    assert "diagnostic vétérinaire" in provider.seen["system"]
    stored = AIMessage.objects.get(pk=reply["id"])
    assert stored.input_tokens == 10 and stored.output_tokens == 5


def test_history_is_sent_and_failed_turns_excluded(client_for, breeder, conversation, monkeypatch):
    AIMessage.objects.create(conversation=conversation, role="USER", content="Q1")
    AIMessage.objects.create(
        conversation=conversation, role="ASSISTANT", content="Indisponible", error_code="not_configured"
    )
    AIMessage.objects.create(conversation=conversation, role="ASSISTANT", content="R1")
    provider = ScriptedProvider()
    monkeypatch.setattr(orchestrator, "get_llm_provider", lambda: provider)
    client_for(breeder).post(f"{URL}{conversation.pk}/messages/", {"content": "Q2"}, format="json")
    assert provider.seen["history"] == [
        {"role": "user", "content": "Q1"},
        {"role": "assistant", "content": "R1"},
        {"role": "user", "content": "Q2"},
    ]


def test_provider_error_is_stored_and_reported(client_for, breeder, conversation, monkeypatch):
    provider = ScriptedProvider(error=LLMError("provider_rate_limited", "Saturé."))
    monkeypatch.setattr(orchestrator, "get_llm_provider", lambda: provider)
    response = client_for(breeder).post(f"{URL}{conversation.pk}/messages/", {"content": "Q"}, format="json")
    assert response.status_code == 201
    assert response.json()[1]["error_code"] == "provider_rate_limited"


def test_conversations_are_private(client_for, breeder, make_user, conversation):
    other = client_for(make_user())
    assert other.get(URL).json()["count"] == 0
    assert other.get(f"{URL}{conversation.pk}/").status_code == 404
    assert other.post(f"{URL}{conversation.pk}/messages/", {"content": "x"}, format="json").status_code == 404
    assert other.delete(f"{URL}{conversation.pk}/").status_code == 404


def test_cannot_attach_conversation_to_foreign_farm(client_for, make_user, farm):
    response = client_for(make_user()).post(URL, {"farm": farm.pk}, format="json")
    assert response.status_code == 400


def test_empty_question_rejected(client_for, breeder, conversation):
    response = client_for(breeder).post(f"{URL}{conversation.pk}/messages/", {"content": "  "}, format="json")
    assert response.status_code == 400


def test_delete_conversation(client_for, breeder, conversation):
    AIMessage.objects.create(conversation=conversation, role="USER", content="Q1")
    assert client_for(breeder).delete(f"{URL}{conversation.pk}/").status_code == 204
    assert not AIMessage.objects.exists()


# --- Outils et permissions ------------------------------------------------------------------


def test_tools_only_see_accessible_farms(breeder, make_user, make_farm, ovin, animal):
    from animals.models import Animal

    stranger_farm = make_farm(owner=make_user(), name="Ferme voisine")
    secret = Animal.objects.create(farm=stranger_farm, species=ovin, tag_number="SECRET-1", sex="F")
    ctx = ToolContext(breeder)
    found = json.loads(ctx.execute("find_animals", {"search": ""})[0])
    assert [a["numero"] for a in found["animaux"]] == ["SN-001"]
    output, ok = ctx.execute("get_animal_growth", {"animal_id": secret.pk})
    assert not ok and "non accessible" in output
    output, ok = ctx.execute("list_groups", {"farm_id": stranger_farm.pk})
    assert not ok


def test_conversation_farm_scope_limits_tools(breeder, farm, make_farm, ovin, animal):
    from animals.models import Animal

    second = make_farm(owner=breeder, name="Deuxième")
    Animal.objects.create(farm=second, species=ovin, tag_number="B-2", sex="F")
    data = json.loads(ToolContext(breeder, farm).execute("find_animals", {})[0])
    assert data["total"] == 1


def test_unknown_tool_and_bad_arguments(breeder):
    ctx = ToolContext(breeder)
    assert ctx.execute("drop_database", {})[1] is False
    assert ctx.execute("get_animal_growth", {"wrong": 1})[1] is False


def test_animal_growth_tool(breeder, animal):
    from datetime import date

    from growth.models import Weighing

    Weighing.objects.create(animal=animal, weighed_on=date(2026, 9, 1), weight_kg=30)
    Weighing.objects.create(animal=animal, weighed_on=date(2026, 9, 11), weight_kg=32)
    ctx = ToolContext(breeder)
    data = json.loads(ctx.execute("get_animal_growth", {"animal_id": animal.pk})[0])
    assert data["gmd_global"]["adg_g_per_day"] == "200.0" or data["gmd_global"]["adg_g_per_day"].startswith(
        "200"
    )
    assert ctx.provenance[0]["type"] == "database"


def test_formula_result_tool_reports_engine_provenance(breeder, farm, ovin):
    from formulations.models import FeedFormula

    formula = FeedFormula.objects.create(
        farm=farm,
        name="Essai",
        species=ovin,
        mode="ECONOMIC",
        status="REFUSED",
        result_snapshot={"refusal_reasons": ["Aucune référence nutritionnelle validée."]},
    )
    ctx = ToolContext(breeder)
    data = json.loads(ctx.execute("get_formula_result", {"formula_id": formula.pk})[0])
    assert data["raisons_du_refus"] == ["Aucune référence nutritionnelle validée."]
    assert data["valide_par_un_expert"] is False
    assert ctx.provenance[0]["type"] == "engine"


def test_readiness_tool_lists_missing_data(breeder, farm):
    data = json.loads(ToolContext(breeder).execute("check_formulation_readiness", {})[0])
    assert data["calcul_possible"] is False
    assert len(data["manques"]) == 3


def test_feeding_cost_tool_without_records(breeder, farm):
    data = json.loads(ToolContext(breeder).execute("get_feeding_cost", {"days": 7})[0])
    assert data["distributions"] == 0 and data["cout_estime_fcfa"] is None


def test_search_documents_tool_without_documents(breeder):
    data = json.loads(ToolContext(breeder).execute("search_documents", {"query": "mouton"})[0])
    assert data["extraits"] == []


def test_alerts_tool(breeder, farm):
    from alerts.models import Alert

    Alert.objects.create(
        farm=farm,
        alert_type="MISSING_WEIGHING",
        severity="WARNING",
        title="Pesée",
        message="m",
        rule_code="r",
        dedup_key="k",
    )
    data = json.loads(ToolContext(breeder).execute("list_open_alerts", {})[0])
    assert data["total_ouvertes"] == 1


def test_all_tool_specs_have_handlers():
    for spec in TOOL_SPECS:
        assert hasattr(ToolContext, f"tool_{spec.name}")
        assert spec.parameters["type"] == "object"


# --- Adaptateurs ----------------------------------------------------------------------------

TOOLS = [ToolSpec("list_my_farms", "Liste", {"type": "object", "properties": {}})]


def _executor(log):
    def execute(name, args):
        log.append((name, args))
        return '{"ok": 1}', True

    return execute


def test_openai_compatible_tool_loop():
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        assert request.headers["Authorization"] == "Bearer k"
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "c1",
                                        "type": "function",
                                        "function": {"name": "list_my_farms", "arguments": "{}"},
                                    }
                                ],
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 1},
                },
            )
        assert body["messages"][-1] == {"role": "tool", "tool_call_id": "c1", "content": '{"ok": 1}'}
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Réponse"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        )

    log = []
    provider = OpenAICompatibleProvider(
        "m",
        api_key="k",
        base_url="http://llm/v1/",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = provider.run("sys", [{"role": "user", "content": "Q"}], TOOLS, _executor(log))
    assert result.text == "Réponse" and log == [("list_my_farms", {})]
    assert (result.input_tokens, result.output_tokens) == (8, 3)
    assert requests[0]["messages"][0] == {"role": "system", "content": "sys"}
    assert requests[0]["tools"][0]["function"]["name"] == "list_my_farms"


@pytest.mark.parametrize(
    "status, code", [(401, "provider_auth"), (429, "provider_rate_limited"), (500, "provider_error")]
)
def test_http_errors_are_mapped(status, code):
    provider = OllamaProvider(
        "m",
        base_url="http://ollama",
        client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status))),
    )
    with pytest.raises(LLMError) as exc:
        provider.run("sys", [{"role": "user", "content": "Q"}], TOOLS, _executor([]))
    assert exc.value.code == code


def test_unreachable_provider():
    def handler(request):
        raise httpx.ConnectError("refusé")

    provider = OllamaProvider(
        "m", base_url="http://ollama", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(LLMError) as exc:
        provider.run("sys", [], TOOLS, _executor([]))
    assert exc.value.code == "provider_unreachable"


def test_ollama_tool_loop():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert request.url.path == "/api/chat" and body["stream"] is False
        if len(calls) == 1:
            return httpx.Response(
                200,
                json={
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{"function": {"name": "list_my_farms", "arguments": {}}}],
                    }
                },
            )
        return httpx.Response(
            200, json={"message": {"content": "Fini"}, "done_reason": "stop", "eval_count": 4}
        )

    log = []
    provider = OllamaProvider(
        "m", base_url="http://ollama", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = provider.run("sys", [{"role": "user", "content": "Q"}], TOOLS, _executor(log))
    assert result.text == "Fini" and log == [("list_my_farms", {})]
    assert calls[1]["messages"][-1]["role"] == "tool"


def test_tool_loop_is_bounded():
    def handler(request):
        return httpx.Response(
            200, json={"message": {"tool_calls": [{"function": {"name": "list_my_farms", "arguments": {}}}]}}
        )

    provider = OllamaProvider(
        "m", base_url="http://o", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(LLMError) as exc:
        provider.run("sys", [], TOOLS, _executor([]), max_rounds=2)
    assert exc.value.code == "too_many_tool_calls"


def _block(**kw):
    return SimpleNamespace(**kw)


class FakeMessages:
    def __init__(self, responses):
        self.responses, self.requests = list(responses), []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)


def _fake_anthropic(responses):
    messages = FakeMessages(responses)
    return SimpleNamespace(messages=messages, beta=SimpleNamespace(messages=messages)), messages


def test_anthropic_tool_loop_uses_fallbacks():
    tool_use = _block(type="tool_use", id="tu1", name="list_my_farms", input={})
    first = SimpleNamespace(
        stop_reason="tool_use",
        content=[_block(type="text", text="Je regarde."), tool_use],
        usage=SimpleNamespace(input_tokens=7, output_tokens=2),
    )
    final = SimpleNamespace(
        stop_reason="end_turn",
        content=[_block(type="text", text="Vous avez 1 ferme.")],
        usage=SimpleNamespace(input_tokens=9, output_tokens=4),
    )
    client, messages = _fake_anthropic([first, final])
    log = []
    provider = AnthropicProvider("claude-opus-5-5", api_key="k", client=client)
    result = provider.run("sys", [{"role": "user", "content": "Q"}], TOOLS, _executor(log))
    assert result.text == "Vous avez 1 ferme." and log == [("list_my_farms", {})]
    assert (result.input_tokens, result.output_tokens) == (16, 6)
    req = messages.requests[0]
    assert req["model"] == "claude-opus-5-5" and req["fallbacks"] == "default"
    assert req["betas"] == ["server-side-fallback-2026-07-01"]
    assert req["tools"][0]["input_schema"] == TOOLS[0].parameters
    second = messages.requests[1]["messages"]
    assert second[1] == {"role": "assistant", "content": first.content}  # renvoyé tel quel
    assert second[2]["content"] == [
        {"type": "tool_result", "tool_use_id": "tu1", "content": '{"ok": 1}', "is_error": False}
    ]


def test_anthropic_without_fallbacks_and_refusal():
    refusal = SimpleNamespace(stop_reason="refusal", content=[], usage=None)
    client, messages = _fake_anthropic([refusal])
    provider = AnthropicProvider("claude-opus-5-5", api_key="k", client=client, use_fallbacks=False)
    with pytest.raises(LLMError) as exc:
        provider.run("sys", [{"role": "user", "content": "Q"}], TOOLS, _executor([]))
    assert exc.value.code == "provider_refusal"
    assert "fallbacks" not in messages.requests[0]


def test_anthropic_sdk_errors_are_mapped():
    import anthropic

    class Failing:
        def create(self, **kwargs):
            raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))

    client = SimpleNamespace(messages=Failing(), beta=SimpleNamespace(messages=Failing()))
    provider = AnthropicProvider("claude-opus-5-5", api_key="k", client=client)
    with pytest.raises(LLMError) as exc:
        provider.run("sys", [{"role": "user", "content": "Q"}], TOOLS, _executor([]))
    assert exc.value.code == "provider_unreachable"

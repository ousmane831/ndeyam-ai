"""
Fournisseurs de LLM interchangeables (LLM_PROVIDER dans `.env`).

| LLM_PROVIDER      | Implémentation                                                    |
|-------------------|-------------------------------------------------------------------|
| none              | assistant désactivé (le reste de l'application fonctionne)        |
| anthropic         | SDK officiel `anthropic` (Claude) — modèle par défaut claude-opus-5-5 |
| openai_compatible | POST {LLM_BASE_URL}/chat/completions (appel d'outils « functions ») |
| ollama            | POST {LLM_BASE_URL}/api/chat (modèle local)                        |

Chaque fournisseur exécute la boucle d'outils dans son format natif : le modèle demande un outil,
l'orchestrateur l'exécute (avec les permissions de l'utilisateur) et renvoie le résultat, jusqu'à la
réponse finale. Le modèle ne calcule rien lui-même : les chiffres viennent des outils.
"""

import json
import logging
import time
from dataclasses import dataclass, field

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    """Erreur du fournisseur, avec un code stable et un message lisible en français."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # schéma JSON des arguments


@dataclass
class LLMResult:
    text: str
    tool_calls: list = field(default_factory=list)  # [{"name", "input", "ok"}]
    input_tokens: int | None = None
    output_tokens: int | None = None
    stop_reason: str = ""
    latency_ms: int = 0


class LLMProvider:
    name = "none"

    def __init__(self, model, api_key="", base_url="", timeout=60, client=None):
        self.model = model
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout
        self.client = client

    def run(self, system, history, tools, execute_tool, max_rounds=6) -> LLMResult:
        """`history` : [{"role": "user"|"assistant", "content": str}] ; `execute_tool(name, input) -> str`."""
        started = time.monotonic()
        result = self._run(system, history, tools, execute_tool, max_rounds)
        result.latency_ms = int((time.monotonic() - started) * 1000)
        return result

    def _run(self, system, history, tools, execute_tool, max_rounds):  # pragma: no cover - surchargé
        raise NotImplementedError


def _too_many_rounds():
    return LLMError(
        "too_many_tool_calls", "L'assistant a dépassé le nombre d'étapes autorisé pour cette question."
    )


# --- Claude (SDK officiel) -------------------------------------------------------------


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, *args, use_fallbacks=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_fallbacks = use_fallbacks
        if self.client is None:
            import anthropic

            self.client = anthropic.Anthropic(
                api_key=self.api_key, base_url=self.base_url or None, timeout=self.timeout, max_retries=2
            )

    def _create(self, system, messages, tools):
        params = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": messages,
            "tools": [
                {"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools
            ],
            "output_config": {"effort": "medium"},
        }
        if self.use_fallbacks:
            # Repli côté serveur si les classificateurs refusent la réponse (désactivable : LLM_FALLBACKS).
            return self.client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **params)
        return self.client.messages.create(**params)

    def _run(self, system, history, tools, execute_tool, max_rounds):
        import anthropic

        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        calls, tokens_in, tokens_out = [], 0, 0
        for _ in range(max_rounds):
            try:
                response = self._create(system, messages, tools)
            except anthropic.AuthenticationError as exc:
                raise LLMError(
                    "provider_auth", "Clé API du fournisseur refusée : vérifiez LLM_API_KEY."
                ) from exc
            except anthropic.RateLimitError as exc:
                raise LLMError(
                    "provider_rate_limited",
                    "Le fournisseur d'IA est momentanément saturé. Réessayez dans un instant.",
                ) from exc
            except anthropic.APIConnectionError as exc:
                raise LLMError(
                    "provider_unreachable", "Le fournisseur d'IA est injoignable (réseau ou délai dépassé)."
                ) from exc
            except anthropic.APIStatusError as exc:
                raise LLMError(
                    "provider_error", f"Le fournisseur d'IA a répondu une erreur ({exc.status_code})."
                ) from exc
            usage = getattr(response, "usage", None)
            tokens_in += getattr(usage, "input_tokens", 0) or 0
            tokens_out += getattr(usage, "output_tokens", 0) or 0
            if response.stop_reason == "refusal":
                raise LLMError("provider_refusal", "Le modèle a refusé de répondre à cette demande.")
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason != "tool_use" or not tool_uses:
                text = "\n".join(b.text for b in response.content if b.type == "text").strip()
                if response.stop_reason == "max_tokens":
                    text += "\n\n(Réponse tronquée : la limite de longueur a été atteinte.)"
                return LLMResult(text, calls, tokens_in, tokens_out, response.stop_reason)
            # Le contenu de l'assistant (y compris les blocs de réflexion) est renvoyé tel quel.
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in tool_uses:
                output, ok = execute_tool(block.name, block.input)
                calls.append({"name": block.name, "input": block.input, "ok": ok})
                results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": output, "is_error": not ok}
                )
            messages.append({"role": "user", "content": results})
        raise _too_many_rounds()


# --- Fournisseurs HTTP (compatible OpenAI, Ollama) ---------------------------------------


class _HttpProvider(LLMProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = self.client or httpx.Client(timeout=self.timeout)

    def _post(self, url, payload, headers=None):
        try:
            response = self.client.post(url, json=payload, headers=headers or {})
        except httpx.HTTPError as exc:
            raise LLMError(
                "provider_unreachable", "Le fournisseur d'IA est injoignable (réseau ou délai dépassé)."
            ) from exc
        if response.status_code in (401, 403):
            raise LLMError("provider_auth", "Clé API du fournisseur refusée : vérifiez LLM_API_KEY.")
        if response.status_code == 429:
            raise LLMError(
                "provider_rate_limited",
                "Le fournisseur d'IA est momentanément saturé. Réessayez dans un instant.",
            )
        if response.status_code >= 400:
            raise LLMError(
                "provider_error", f"Le fournisseur d'IA a répondu une erreur ({response.status_code})."
            )
        return response.json()

    @staticmethod
    def _function_tools(tools):
        return [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
            }
            for t in tools
        ]


class OpenAICompatibleProvider(_HttpProvider):
    name = "openai_compatible"

    def _run(self, system, history, tools, execute_tool, max_rounds):
        messages = [{"role": "system", "content": system}, *history]
        calls, tokens_in, tokens_out = [], 0, 0
        for _ in range(max_rounds):
            data = self._post(
                f"{self.base_url}/chat/completions",
                {"model": self.model, "messages": messages, "tools": self._function_tools(tools)},
                {"Authorization": f"Bearer {self.api_key}"},
            )
            usage = data.get("usage") or {}
            tokens_in += usage.get("prompt_tokens", 0)
            tokens_out += usage.get("completion_tokens", 0)
            choice = (data.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return LLMResult(
                    (message.get("content") or "").strip(),
                    calls,
                    tokens_in,
                    tokens_out,
                    choice.get("finish_reason", ""),
                )
            messages.append(
                {"role": "assistant", "content": message.get("content"), "tool_calls": tool_calls}
            )
            for call in tool_calls:
                fn = call.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args, output, ok = {}, "Erreur : arguments JSON invalides.", False
                else:
                    output, ok = execute_tool(fn.get("name", ""), args)
                calls.append({"name": fn.get("name"), "input": args, "ok": ok})
                messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": output})
        raise _too_many_rounds()


class OllamaProvider(_HttpProvider):
    name = "ollama"

    def _run(self, system, history, tools, execute_tool, max_rounds):
        messages = [{"role": "system", "content": system}, *history]
        calls, tokens_in, tokens_out = [], 0, 0
        for _ in range(max_rounds):
            data = self._post(
                f"{self.base_url}/api/chat",
                {
                    "model": self.model,
                    "messages": messages,
                    "tools": self._function_tools(tools),
                    "stream": False,
                },
            )
            tokens_in += data.get("prompt_eval_count", 0)
            tokens_out += data.get("eval_count", 0)
            message = data.get("message") or {}
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return LLMResult(
                    (message.get("content") or "").strip(),
                    calls,
                    tokens_in,
                    tokens_out,
                    data.get("done_reason", ""),
                )
            messages.append(
                {"role": "assistant", "content": message.get("content", ""), "tool_calls": tool_calls}
            )
            for call in tool_calls:
                fn = call.get("function", {})
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                output, ok = execute_tool(fn.get("name", ""), args)
                calls.append({"name": fn.get("name"), "input": args, "ok": ok})
                messages.append({"role": "tool", "tool_name": fn.get("name"), "content": output})
        raise _too_many_rounds()


PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai_compatible": OpenAICompatibleProvider,
    "ollama": OllamaProvider,
}


def configuration_problem(config=None) -> str | None:
    config = config or settings.LLM
    provider = config["PROVIDER"]
    if provider in ("", "none"):
        return "L'assistant IA n'est pas configuré (LLM_PROVIDER=none)."
    if provider not in PROVIDERS:
        return f"Fournisseur LLM inconnu : « {provider} »."
    if provider in ("anthropic", "openai_compatible") and not config["API_KEY"]:
        return "LLM_API_KEY doit être renseignée pour ce fournisseur."
    if provider in ("openai_compatible", "ollama") and not config["BASE_URL"]:
        return "LLM_BASE_URL doit être renseignée pour ce fournisseur."
    if provider != "anthropic" and not config["MODEL"]:
        return "LLM_MODEL doit être renseigné pour ce fournisseur."
    return None


def get_llm_provider(client=None) -> LLMProvider | None:
    config = settings.LLM
    if configuration_problem(config):
        return None
    provider = config["PROVIDER"]
    model = config["MODEL"] or DEFAULT_ANTHROPIC_MODEL
    kwargs = {
        "api_key": config["API_KEY"],
        "base_url": config["BASE_URL"],
        "timeout": config["TIMEOUT_SECONDS"],
        "client": client,
    }
    if provider == "anthropic":
        kwargs["use_fallbacks"] = config.get("FALLBACKS", True)
    return PROVIDERS[provider](model, **kwargs)

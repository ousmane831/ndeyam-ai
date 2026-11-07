"""
Orchestrateur de l'assistant NDEYAM AI.

Question → historique de la conversation → LLM avec outils métier (droits de l'utilisateur)
→ réponse enregistrée avec la provenance de chaque information.
"""

from django.utils import timezone

from governance.activity import log_activity

from .llm import LLMError, configuration_problem, get_llm_provider
from .models import AIMessage, MessageRole
from .tools import TOOL_SPECS, ToolContext

HISTORY_LIMIT = 20
MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = "\n".join(
    [
        "Tu es l'assistant de NDEYAM AI, une plateforme d'aide à la gestion des élevages (ovins en priorité) "
        "au Sénégal et en Afrique de l'Ouest. Tu réponds en français, de façon claire et concrète, "
        "à des éleveurs et à des techniciens.",
        "",
        "Règles impératives :",
        "1. Les chiffres (poids, GMD, coûts, apports, rations) proviennent UNIQUEMENT des outils. "
        "Tu ne calcules jamais toi-même une ration, des besoins nutritionnels ou une composition : "
        "tu expliques les résultats du moteur nutritionnel (outil get_formula_result) et des données "
        "enregistrées. Pour une nouvelle formule, oriente vers la page « Formulation des aliments ».",
        "2. Si une information manque ou n'est pas validée, dis-le clairement et indique comment la "
        "compléter. N'invente rien.",
        "3. Distingue toujours l'origine de ce que tu dis : « D'après vos données… », « Selon le document X, "
        "p. Y… », « Le moteur nutritionnel indique… ». Ce que tu ajoutes de toi-même est une explication "
        "générale, à présenter comme telle.",
        "4. Une formule au statut « Estimation mathématique » n'est pas une recommandation validée : "
        "rappelle-le.",
        "5. Tu ne poses jamais de diagnostic vétérinaire et tu ne prescris aucun traitement. "
        "Pour toute question de santé, recommande de consulter un vétérinaire.",
        "6. Les données DEMO sont fictives : signale-le lorsqu'elles apparaissent.",
        "7. Cite les documents sous la forme fournie par l'outil search_documents.",
        "Sois concis : quelques phrases ou une courte liste suffisent généralement.",
    ]
)

UNAVAILABLE = (
    "L'assistant IA n'est pas configuré sur cette installation. Les autres modules "
    "(animaux, pesées, formulation, "
    "rations, base documentaire) restent entièrement utilisables."
)


def assistant_status():
    from django.conf import settings

    problem = configuration_problem()
    return {
        "configured": problem is None,
        "provider": settings.LLM["PROVIDER"] if problem is None else None,
        "model": (get_llm_provider().model if problem is None else None),
        "message": problem or "Assistant disponible.",
    }


def _history(conversation):
    rows = conversation.messages.filter(
        role__in=[MessageRole.USER, MessageRole.ASSISTANT], error_code=""
    ).order_by("-created_at", "-id")
    history = [
        {"role": "user" if m.role == MessageRole.USER else "assistant", "content": m.content}
        for m in reversed(rows[:HISTORY_LIMIT])
    ]
    while history and history[0]["role"] != "user":
        history.pop(0)  # l'historique commence toujours par une question
    return history


def ask(conversation, question, request=None, provider="auto"):
    """Enregistre la question, interroge le LLM et enregistre la réponse.

    Retourne (message_utilisateur, réponse)."""
    user_message = AIMessage.objects.create(
        conversation=conversation, role=MessageRole.USER, content=question
    )
    if not conversation.title:
        conversation.title = question[:80]
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=["title", "updated_at"])

    provider = get_llm_provider() if provider == "auto" else provider
    if provider is None:
        reply = AIMessage.objects.create(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content=UNAVAILABLE,
            error_code="not_configured",
        )
        return user_message, reply

    context = ToolContext(conversation.user, conversation.farm)
    try:
        result = provider.run(
            SYSTEM_PROMPT, _history(conversation), TOOL_SPECS, context.execute, MAX_TOOL_ROUNDS
        )
    except LLMError as exc:
        reply = AIMessage.objects.create(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content=exc.message,
            error_code=exc.code,
            provider=provider.name,
            model=provider.model,
            provenance=context.provenance,
        )
        log_activity(
            request, "assistant.error", conversation, actor=conversation.user, details={"code": exc.code}
        )
        return user_message, reply

    text = result.text or "Je n'ai pas pu formuler de réponse. Reformulez votre question."
    provenance = [
        *context.provenance,
        {"type": "llm", "label": "Rédaction et explications générées par le modèle de langage"},
    ]
    reply = AIMessage.objects.create(
        conversation=conversation,
        role=MessageRole.ASSISTANT,
        content=text,
        provenance=provenance,
        tool_calls=result.tool_calls,
        provider=provider.name,
        model=provider.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=result.latency_ms,
    )
    log_activity(
        request,
        "assistant.answered",
        conversation,
        actor=conversation.user,
        details={"tools": [c["name"] for c in result.tool_calls]},
    )
    return user_message, reply

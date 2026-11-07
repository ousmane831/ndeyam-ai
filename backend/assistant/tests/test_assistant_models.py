import pytest

from assistant.models import AIConversation, AIMessage

pytestmark = pytest.mark.django_db


def test_conversation_keeps_messages_in_order_with_provenance(breeder):
    conversation = AIConversation.objects.create(user=breeder, title="Suivi du lot")
    AIMessage.objects.create(conversation=conversation, role="USER", content="Quel est le poids de SN-001 ?")
    AIMessage.objects.create(
        conversation=conversation,
        role="ASSISTANT",
        content="Le dernier poids enregistré est 32 kg.",
        provenance=[{"type": "database", "label": "Pesée du 01/11/2026"}],
    )
    messages = list(conversation.messages.all())
    assert [m.role for m in messages] == ["USER", "ASSISTANT"]
    assert messages[1].provenance[0]["type"] == "database"


def test_deleting_user_deletes_private_conversations(breeder):
    AIConversation.objects.create(user=breeder)
    breeder.delete()
    assert not AIConversation.objects.exists()

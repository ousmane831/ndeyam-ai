from django.urls import path

from .views import VoiceAnswerView, VoiceAskView, VoiceStatusView

urlpatterns = [
    path("voice/status/", VoiceStatusView.as_view(), name="voice-status"),
    path("voice/ask/", VoiceAskView.as_view(), name="voice-ask"),
    path("voice/answer/", VoiceAnswerView.as_view(), name="voice-answer"),
]

from rest_framework.routers import SimpleRouter

from .views import ConversationViewSet

router = SimpleRouter()
router.register("assistant/conversations", ConversationViewSet, basename="assistant-conversation")

urlpatterns = router.urls

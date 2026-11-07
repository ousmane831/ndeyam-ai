from rest_framework.routers import SimpleRouter

from .views import TechnicalDocumentViewSet

router = SimpleRouter()
router.register("documents", TechnicalDocumentViewSet, basename="document")

urlpatterns = router.urls

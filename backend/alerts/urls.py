from rest_framework.routers import SimpleRouter

from .views import AlertRuleViewSet, AlertViewSet

router = SimpleRouter()
router.register("alerts", AlertViewSet, basename="alert")
router.register("alert-rules", AlertRuleViewSet, basename="alert-rule")

urlpatterns = router.urls

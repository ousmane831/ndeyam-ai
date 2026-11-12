from rest_framework.routers import SimpleRouter

from .views import FeedFormulaViewSet, RationTemplateViewSet

router = SimpleRouter()
router.register("formulas", FeedFormulaViewSet, basename="formula")
router.register("ration-templates", RationTemplateViewSet, basename="ration-template")

urlpatterns = router.urls

from rest_framework.routers import SimpleRouter

from .views import FeedFormulaViewSet

router = SimpleRouter()
router.register("formulas", FeedFormulaViewSet, basename="formula")

urlpatterns = router.urls

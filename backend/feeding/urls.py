from rest_framework.routers import SimpleRouter

from .views import FeedingRecordViewSet, RationViewSet

router = SimpleRouter()
router.register("rations", RationViewSet, basename="ration")
router.register("feeding-records", FeedingRecordViewSet, basename="feeding-record")

urlpatterns = router.urls

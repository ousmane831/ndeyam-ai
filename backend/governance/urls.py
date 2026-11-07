from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("sources", views.SourceDocumentViewSet, basename="source")
router.register("validation-records", views.ValidationRecordViewSet, basename="validation-record")
router.register("import-batches", views.ImportBatchViewSet, basename="import-batch")
router.register("activity-logs", views.ActivityLogViewSet, basename="activity-log")

urlpatterns = router.urls

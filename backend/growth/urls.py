from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("weighings", views.WeighingViewSet, basename="weighing")
router.register("growth-ranges", views.GrowthRangeViewSet, basename="growth-range")

urlpatterns = [
    *router.urls,
    path("growth/animals/<int:pk>/", views.AnimalGrowthView.as_view(), name="growth-animal"),
    path("growth/groups/<int:pk>/", views.GroupGrowthView.as_view(), name="growth-group"),
    path("growth/overview/", views.FarmGrowthOverviewView.as_view(), name="growth-overview"),
    path("growth/prediction-status/", views.PredictionStatusView.as_view(), name="growth-prediction-status"),
]

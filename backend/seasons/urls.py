from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("seasons", views.SeasonViewSet, basename="season")
router.register(
    "ingredient-availability", views.IngredientAvailabilityViewSet, basename="ingredient-availability"
)
router.register("seasonal-advice", views.SeasonalAdviceViewSet, basename="seasonal-advice")

urlpatterns = [
    path("seasons/current/", views.CurrentSeasonView.as_view(), name="season-current"),
    *router.urls,
]

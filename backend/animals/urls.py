from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("species", views.SpeciesViewSet, basename="species")
router.register("breeds", views.BreedViewSet, basename="breed")
router.register("animal-categories", views.AnimalCategoryViewSet, basename="animal-category")
router.register("physiological-stages", views.PhysiologicalStageViewSet, basename="physiological-stage")
router.register("production-objectives", views.ProductionObjectiveViewSet, basename="production-objective")
router.register("groups", views.AnimalGroupViewSet, basename="group")
router.register("animals", views.AnimalViewSet, basename="animal")

observations = views.AnimalObservationViewSet.as_view({"get": "list", "post": "create"})
observation_detail = views.AnimalObservationViewSet.as_view({"delete": "destroy"})

urlpatterns = [
    *router.urls,
    path("animals/<int:animal_pk>/observations/", observations, name="animal-observation-list"),
    path(
        "animals/<int:animal_pk>/observations/<int:pk>/", observation_detail, name="animal-observation-detail"
    ),
]

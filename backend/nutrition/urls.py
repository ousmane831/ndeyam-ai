from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("nutrition-systems", views.NutritionSystemViewSet, basename="nutrition-system")
router.register("nutrients", views.NutrientViewSet, basename="nutrient")
router.register("ingredient-categories", views.IngredientCategoryViewSet, basename="ingredient-category")
router.register("ingredients", views.IngredientViewSet, basename="ingredient")
router.register("compositions", views.CompositionViewSet, basename="composition")
router.register("ingredient-prices", views.IngredientPriceViewSet, basename="ingredient-price")
router.register("nutritional-references", views.ReferenceViewSet, basename="nutritional-reference")
router.register("requirements", views.RequirementViewSet, basename="requirement")
router.register("inclusion-constraints", views.InclusionConstraintViewSet, basename="inclusion-constraint")

urlpatterns = router.urls

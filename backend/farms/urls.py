from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import FarmMemberViewSet, FarmViewSet

router = DefaultRouter()
router.register("farms", FarmViewSet, basename="farm")

member_list = FarmMemberViewSet.as_view({"get": "list", "post": "create"})
member_detail = FarmMemberViewSet.as_view({"patch": "partial_update", "delete": "destroy"})

urlpatterns = [
    *router.urls,
    path("farms/<int:farm_pk>/members/", member_list, name="farm-member-list"),
    path("farms/<int:farm_pk>/members/<int:pk>/", member_detail, name="farm-member-detail"),
]

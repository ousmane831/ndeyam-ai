"""Routes principales de NDEYAM AI. Toutes les routes métier sont versionnées sous /api/v1/."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from accounts.urls import admin_router, auth_urlpatterns
from core.dashboard import DashboardView
from core.views import HealthView

admin.site.site_header = "NDEYAM AI — Administration"
admin.site.site_title = "NDEYAM AI"
admin.site.index_title = "Gestion de la plateforme"

api_v1 = [
    path("health/", HealthView.as_view(), name="health"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("auth/", include(auth_urlpatterns)),
    path("admin/", include(admin_router.urls)),
    path("", include("farms.urls")),
    path("", include("animals.urls")),
    path("", include("nutrition.urls")),
    path("", include("formulations.urls")),
    path("", include("feeding.urls")),
    path("", include("governance.urls")),
    path("", include("growth.urls")),
    path("", include("alerts.urls")),
    path("", include("knowledge_base.urls")),
    path("", include("assistant.urls")),
    path("", include("seasons.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

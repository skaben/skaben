from core import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from core.admin import base_site
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from alert.urls import router as alert_router
from assets.urls import router as assets_router

from peripheral_behavior.urls import router as behavior_router
from peripheral_devices.urls import router as device_router
from streams.urls import router as stream_router


urlpatterns = [
    path("admin/", base_site.urls),
    path("api/assets/", include((assets_router.urls, "assets"), namespace="assets")),
    path("api/alert/", include((alert_router.urls, "alert"), namespace="alert")),
    path("api/streams/", include((stream_router.urls, "streams"), namespace="streams")),
    path("api/devices/", include((device_router.urls, "devices"), namespace="devices")),
    path("api/behavior/", include((behavior_router.urls, "behavior"), namespace="behavior")),
    path("api/auth/token/", views.CreateTokenView.as_view(), name="token"),
    path("api/auth/login/", views.login_view, name="login"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("ops/update-devices/", views.UpdateDeviceView.as_view(), name="update-devices"),
    path("ops/healthcheck/", views.health_check, name="healthcheck"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()

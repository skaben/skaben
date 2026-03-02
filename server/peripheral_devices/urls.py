from django.urls import include, path
from peripheral_devices import views
from rest_framework.routers import SimpleRouter

app_name = "device"

router = SimpleRouter()
router.register("lock", views.LockViewSet)
router.register("terminal", views.TerminalViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

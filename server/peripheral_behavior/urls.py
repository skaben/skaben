from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import MenuViewSet, TerminalAccountViewSet

app_name = "behavior"

router = SimpleRouter()
router.register("menu", MenuViewSet)
router.register("account", TerminalAccountViewSet)

urlpatterns = [path("", include(router.urls))]

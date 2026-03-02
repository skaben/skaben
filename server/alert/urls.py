from alert import views
from django.urls import include, path
from rest_framework.routers import SimpleRouter

app_name = "alert"

router = SimpleRouter()
router.register("alert_state", views.AlertStateViewSet)
router.register("alert_counter", views.AlertCounterViewSet)

urlpatterns = [path("", include((router.urls, "alert")))]

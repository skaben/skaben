from django.urls import include, path
from rest_framework.routers import SimpleRouter
from streams import views

app_name = "events"

router = SimpleRouter()
router.register("events", views.EventViewSet)

urlpatterns = [path("", include(router.urls))]

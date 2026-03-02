from alert import serializers
from core.views import DynamicAuthMixin
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AlertCounter, AlertState, ALERT_COUNTER, ALERT_STATE
from .service import AlertService


class AlertStateViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet, DynamicAuthMixin):
    """Global alert state viewset"""

    queryset = AlertState.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["current"]

    def get_serializer_class(cls):
        if cls.action == "list":
            return serializers.AlertStateSerializer
        if cls.action == "set_current":
            return serializers.AlertStateSetCurrentSerializer
        else:
            return serializers.AlertStateSerializer

    @action(detail=True, methods=["post"])
    def set_current(self, request, pk=None):
        """Set Alert State as current"""
        try:
            state = self.queryset.get(id=pk)
            with AlertService(init_by=ALERT_STATE) as service:
                service.set_state_current(state)
            serializer_resp = serializers.AlertStateSerializer(state)
            return Response(serializer_resp.data)
        except AlertState.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class AlertCounterViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    """
    Alert counter viewset
    """

    queryset = AlertCounter.objects.all()
    serializer_class = serializers.AlertCounterSerializer

    @staticmethod
    def _get_latest():
        with AlertService(init_by=ALERT_COUNTER) as service:
            state = service.get_state_current()
            service.get_last_counter(backup_value=state.threshold)
        return AlertCounter.objects.last()

    @action(methods=["get"], detail=False)
    def get_latest(self, *args, **kwargs):
        latest = self._get_latest()
        serializer = self.get_serializer(latest)
        return Response(serializer.data)

    @action(detail=False, description="Удаление истории счетчиков")
    def purge_history(self, request):
        latest = self._get_latest()
        AlertCounter.objects.exclude(id=latest.id)

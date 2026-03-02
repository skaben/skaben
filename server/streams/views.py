from core.views import DynamicAuthMixin
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from streams import serializers

from .models import StreamRecord


class EventViewSet(viewsets.ModelViewSet, DynamicAuthMixin):
    """Events in database"""

    queryset = StreamRecord.objects.all()
    serializer_class = serializers.StreamRecordSerializer

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["level", "source", "stream", "mark"]
    ordering_fields = ["timestamp", "stream", "source"]
    ordering = ("timestamp",)

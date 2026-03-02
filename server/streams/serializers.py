from rest_framework import serializers
from streams.models import StreamRecord


class StreamRecordSerializer(serializers.ModelSerializer):
    """Serializer for event objects"""

    human_time = serializers.ReadOnlyField()

    class Meta:
        model = StreamRecord
        exclude = ("uuid",)

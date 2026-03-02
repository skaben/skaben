from alert.models import AlertCounter, AlertState
from rest_framework import serializers


class AlertStateSerializer(serializers.ModelSerializer):
    """Global Alert State serializer"""

    class Meta:
        model = AlertState
        fields = "__all__"


class AlertStateSetCurrentSerializer(serializers.ModelSerializer):
    """Global Alert State serializer"""

    class Meta:
        model = AlertState
        fields = ()


class AlertCounterSerializer(serializers.ModelSerializer):
    """Global alert value counter"""

    class Meta:
        model = AlertCounter
        fields = "__all__"

    def create(self, validated_data: dict) -> AlertCounter:
        alert_value = validated_data.get("value")
        comment = validated_data.get("comment", "value changed by API")
        instance = AlertCounter.objects.create(value=alert_value, comment=comment)
        return instance

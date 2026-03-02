from rest_framework import serializers

from peripheral_devices.models.lock import LockDevice
from peripheral_devices.models.terminal import TerminalDevice
from peripheral_behavior.serializers.menu import TerminalAccountSerializer


class DeviceSerializer(serializers.ModelSerializer):
    topic = serializers.ReadOnlyField()
    hash = serializers.SerializerMethodField()
    alert = serializers.ReadOnlyField()

    class Meta:
        read_only_fields = ("id", "mac_addr", "hash")

    @staticmethod
    def get_hash(obj):
        return obj.get_hash()


class LockSerializer(DeviceSerializer):
    """Lock serializer."""

    online = serializers.ReadOnlyField()
    acl = serializers.SerializerMethodField()

    @staticmethod
    def get_acl(lock):
        return lock.permissions

    @staticmethod
    def get_hash(lock):
        return lock.get_hash()

    class Meta:
        model = LockDevice
        fields = "__all__"
        read_only_fields = ("id", "mac_addr", "timestamp", "online", "acl")


class TerminalSerializer(DeviceSerializer):
    """Terminal serializer."""

    accounts = TerminalAccountSerializer(source="get_related_accounts", many=True)
    account_state_map = serializers.ReadOnlyField(source="get_account_state_map")

    class Meta:
        model = TerminalDevice
        fields = "__all__"
        read_only_fields = ("id", "mac_addr", "timestamp", "alert", "online", "accounts", "account_state_map")

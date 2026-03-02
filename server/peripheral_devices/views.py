from core.views import DynamicAuthMixin
from peripheral_devices.serializers.api import LockSerializer, TerminalSerializer
from peripheral_devices.models.lock import LockDevice
from peripheral_devices.models.terminal import TerminalDevice
from rest_framework import viewsets


class LockViewSet(viewsets.ModelViewSet, DynamicAuthMixin):
    """Manage locks in database"""

    queryset = LockDevice.objects.all()
    serializer_class = LockSerializer


class TerminalViewSet(viewsets.ModelViewSet, DynamicAuthMixin):
    """Manage terminals in database"""

    queryset = TerminalDevice.objects.all()
    serializer_class = TerminalSerializer

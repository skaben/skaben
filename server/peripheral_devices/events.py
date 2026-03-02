from typing import ClassVar

from core.transport.events import SkabenEvent


class DeviceNotFoundEvent(SkabenEvent):
    """Событие не найденного в БД устройства."""

    _event_type: ClassVar[str] = "device_not_found"
    event_type: str = "device_not_found"

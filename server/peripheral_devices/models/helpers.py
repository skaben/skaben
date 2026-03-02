from typing import Type

from peripheral_devices.models.lock import LockDevice
from peripheral_devices.models.terminal import TerminalDevice


def get_model_by_topic(topic: str) -> Type[LockDevice | TerminalDevice]:
    table = {"lock": LockDevice, "terminal": TerminalDevice}
    result = table.get(topic)
    if not result:
        raise ValueError(f"cannot find model by topic: {topic}")
    return result

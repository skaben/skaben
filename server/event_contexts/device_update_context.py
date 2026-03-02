from core.transport.events import SkabenEventContext
from event_contexts.alert.events import AlertStateEvent

from peripheral_devices.models.lock import LockDevice
from peripheral_devices.models.terminal import TerminalDevice


class ClientUpdateContext(SkabenEventContext):
    alert_operations = {
        "lock_block_all": LockDevice.objects.set_blocked_all,
        "terminal_block_all": TerminalDevice.objects.set_blocked_all,
        "lock_close_all": LockDevice.objects.set_closed_all,
        "terminal_power_all": TerminalDevice.objects.set_powered_all,
    }

    def apply(self, event_headers: dict, event_data: dict) -> bool:
        event = AlertStateEvent.from_event_data(event_headers, event_data)
        if not event:
            return False

        payload = {}

        if event.state == "white":
            payload = {
                "terminal_power_all": True,
                "terminal_block_all": False,
                "lock_block_all": False,
                "lock_close_all": True,
            }
        elif event.state == "blue":
            payload = {
                "terminal_power_all": False,
                "terminal_block_all": True,
                "lock_block_all": False,
            }
        elif event.state == "cyan":
            payload = {
                "terminal_power_all": False,
                "lock_block_all": False,
            }
        elif event.state == "black":
            payload = {k: True for k in self.alert_operations.keys()}

        for operation in self.alert_operations.keys():
            value = payload.get(operation)
            if isinstance(value, bool):
                self.alert_operations[operation](value)

        return payload != {}

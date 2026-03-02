import logging
from pydantic import ValidationError

from core.transport.events import SkabenEventContext, ContextEventLevels
from event_contexts.device.events import SkabenDeviceEvent
from event_contexts.device.lock_access_context import LockEventContext
from event_contexts.device.power_shield_context import PowerShieldEventContext
from event_contexts.exceptions import StopContextError


class DeviceEventContext(SkabenEventContext):
    context_dispatcher = {
        "lock": LockEventContext,
        "pwr": PowerShieldEventContext,
    }

    def apply(self, event_headers: dict, event_data: dict):
        logging.debug("applying context `device` for %s %s", event_headers, event_data)
        try:
            event_type = event_headers.get("event_type", "")
            device_type = event_headers.get("device_type", "")
            event_data = event_data.get("payload", {})
            if not SkabenDeviceEvent.has_event_type(event_type):
                logging.debug("cannot handle event - unknown event_type %s", event_type)
                return False
            ctx = self.context_dispatcher.get(device_type)
            if not ctx:
                logging.debug("cannot handle context - unknown device type %s", device_type)
                return False
            with ctx() as context:
                result = context.apply(event_headers=event_headers, event_data=event_data)
                self.events = context.events[:]
                return result
        except StopContextError as e:
            logging.debug("stop context error: %s", e)
            self.add_log_event(message=e.error, level=ContextEventLevels.ERROR)
            return False
        except (ValueError, ValidationError) as e:
            logging.debug("stop context error: %s", e)
            self.add_log_event(message=str(e), level=ContextEventLevels.ERROR)
            return False

from dataclasses import dataclass

from alert.models import AlertState
from alert.service import AlertService
from core.transport.topics import SkabenTopics
from core.transport.events import SkabenEventContext
from event_contexts.alert.events import AlertStateEvent
from event_contexts.exceptions import StopContextError


@dataclass(frozen=True)
class PowerShieldStates:
    POWER_ON = "pwr"
    POWER_AUX = "aux"
    POWER_OFF = "off"

    @property
    def states(self):
        return [self.POWER_AUX, self.POWER_OFF, self.POWER_ON]


class PowerShieldEventContext(SkabenEventContext):
    """Контекст обработки сообщений от силового щитка.

    На этом устройстве работает механизм запуска игровой среды.
    Переключает уровни тревоги из предварительных в игровые в результате решения квеста игроками.
    """

    def apply(self, event_headers: dict, event_data: dict):
        """Меняет уровень тревоги в зависимости от команды щитка."""
        command = event_data.get("powerstate", "").lower()
        device_type = event_headers.get("device_type")

        if command and device_type and device_type.lower() == "pwr":
            shield = PowerShieldStates()

            if command not in shield.states:
                raise StopContextError(f"Powershield command not found in pipeline: `{command}`")

            if command == shield.POWER_OFF:
                # щиток не переключает статус в этом случае
                return

            with AlertService(init_by=SkabenTopics.PWR) as service:
                if command == shield.POWER_AUX:
                    pre_ignition_state = AlertState.objects.is_pre_ignition_state()
                    # щиток переключает статус только из полностью выключенного режима
                    if pre_ignition_state:
                        event = AlertStateEvent(
                            event_source=SkabenTopics.PWR,
                            state="cyan",
                        )
                        self.events.append(event)
                elif command == shield.POWER_ON:
                    # щиток переключает режим в первый игровой статус
                    pre_power_state = AlertState.objects.is_pre_power_state()
                    state = service.get_ingame_states(sort_by="order").first()
                    if pre_power_state and state:
                        event = AlertStateEvent(
                            event_source=SkabenTopics.PWR,
                            state=state.name,
                        )
                        self.events.append(event)

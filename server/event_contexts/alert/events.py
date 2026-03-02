from typing import Literal, Optional, ClassVar

from core.transport.events import SkabenEvent

ALERT_STATE: str = "alert_state"
ALERT_COUNTER: str = "alert_counter"


class AlertStateEvent(SkabenEvent):
    _event_type: ClassVar[str] = ALERT_STATE  # todo: merge with event_type
    event_type: str = ALERT_STATE
    counter_reset: bool = True
    state: str


class AlertCounterEvent(SkabenEvent):
    _event_type: ClassVar[str] = ALERT_COUNTER  # todo: merge with event_type
    event_type: str = ALERT_COUNTER
    value: int
    change: Literal["increase", "decrease", "set"]
    comment: Optional[str]

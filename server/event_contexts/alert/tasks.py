import logging

from typing import Literal, Optional, Tuple

from django.conf import settings

from event_contexts.alert.events import AlertCounterEvent
from alert.models import AlertState, ALERT_INCREASE, ALERT_DECREASE
from alert.service import AlertService


def create_alert_reaction_event(reason: str, change: Literal["increase", "decrease"] = "decrease"):
    state = AlertState.objects.get_current()
    if change == "decrease" and state.counter_decrease:
        value = state.counter_decrease
    elif change == "increase" and state.counter_increase:
        value = state.counter_increase
    else:
        raise ValueError(f"Invalid change parameter: {change}")

    return AlertCounterEvent(
        change=change,
        value=value,
        comment=reason,
    )


def create_alert_auto_event() -> Tuple[Optional[AlertCounterEvent], int]:
    """Создает событие изменения счетчика."""

    with AlertService(init_by="scheduler") as service:
        state = service.get_state_current()
        counter = service.get_last_counter()
        expected_state = service.get_state_by_alert(counter)
        if not state or not expected_state:
            return None, settings.SCHEDULER_TASK_TIMEOUT

        if state.auto_level == 0 or state.auto_timeout == 0:
            return None, settings.SCHEDULER_TASK_TIMEOUT

        if expected_state.ingame and state.ingame and expected_state != state:
            logging.warning("Current AlertCounter is not in current AlertState range.")

        message = ""
        dampener = 30  # смягчает изменение уровня при переходе между состояниями тревоги
        level = state.auto_level
        change_type = state.auto_change

        if state.auto_change == ALERT_INCREASE:
            message = "Auto-increased by regular task"
            next_state = service.get_state_next(state)
            if counter + level > next_state.threshold:
                change_type = "set"
                if not next_state.ingame:
                    level = service.max_alert_value
                elif counter + level > next_state.threshold + dampener:
                    level = next_state.threshold + dampener

        if state.auto_change == ALERT_DECREASE:
            message = "Auto-decreased by regular task"
            prev_state = service.get_state_prev(state)
            if counter - level < state.threshold:
                change_type = "set"
                if not prev_state.ingame:
                    level = state.threshold
                elif counter - level < state.threshold - dampener:
                    level = state.threshold - dampener

        if not message:
            raise ValueError(
                "Field `auto_change` misconfigured (should be `increase` or `decrease` only). Check AlertState model."
            )

        event = AlertCounterEvent(
            event_source="scheduled",
            value=level,
            change=change_type,
            comment=message,
        )
        return event, state.auto_timeout

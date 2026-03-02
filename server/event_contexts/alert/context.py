from typing import Dict

from alert.service import AlertService
from core.helpers import format_routing_key
from core.models.mqtt import DeviceTopic
from core.transport.config import SkabenQueue
from core.transport.publish import get_interface
from core.transport.topics import SkabenTopics
from core.transport.events import SkabenEventContext, ContextEventLevels
from event_contexts.alert.events import (
    ALERT_COUNTER,
    ALERT_STATE,
    AlertCounterEvent,
    AlertStateEvent,
)


class AlertEventContext(SkabenEventContext):
    """Обрабатывает события, связанные с изменением счетчика и уровня тревоги."""

    event_types: Dict[str, AlertStateEvent | AlertCounterEvent] = {
        ALERT_STATE: AlertStateEvent,
        ALERT_COUNTER: AlertCounterEvent,
    }

    def _handle_alert_state_event(self, event: AlertStateEvent):
        """Обработчик события при сохранении нового состояния тревоги.

        Посылает сообщения для апдейта счетчика тревоги.
        Рассылает сообщения с новыми конфигами для устройств.
        """
        source = event.event_source

        # Проверяем, отличается ли имя состояния от текущего - если нужно - переназначаем его.
        # Игнорируем эту процедуру, если событие было только что создано сохраненной моделью AlertState
        if source != ALERT_STATE:
            with AlertService(init_by=source) as service:
                # Если этот уровень тревоги уже назначен - не происходит ничего
                current = service.get_state_current()
                if current and current.name != event.state:
                    # Эта операция создаст новое событие типа alert_state
                    service.set_state_by_name(event.state)
                    return self.add_log_event(f"alert state switched to {event.state}", level=ContextEventLevels.LOG)

        # Если операция не инициирована счетчиком тревоги и необходимо сбросить этот счетчик
        if source != ALERT_COUNTER and event.counter_reset:
            with AlertService(init_by=ALERT_STATE) as service:
                state = service.get_state_by_name(event.state)
                if not state:
                    raise ValueError(f"no state with name {event.state}")
                # эта операция создаст дополнительное событие типа alert_counter
                service.set_alert_counter(value=state.threshold, comment=f"reset by alert state {event.state}")
                self.add_log_event(f"alert counter reset to {event.state} threshold", level=ContextEventLevels.LOG)

        # обновление конфигурации устройств при смене уровня тревоги
        # принудительно посылается CUP запрос, в ответ на который сервер пошлет конфигурации
        for topic in DeviceTopic.objects.get_topics_active():
            with get_interface() as publisher:
                publisher.publish(
                    body={},
                    exchange=publisher.config.exchanges.get("internal"),
                    routing_key=format_routing_key(SkabenQueue.CLIENT_UPDATE.value, topic, "all"),
                )

    def _handle_alert_counter_event(self, event: AlertCounterEvent):
        """Обработчик события при сохранении нового счетчика тревоги

        Отправляет апдейт конфигурации для шкал.
        Отправляет событие для апдейта состояния тревоги, если этот уровень
        является внутриигровым и его порог срабатывания превышен.
        """
        source = event.event_source

        # игнорируем сохранение счетчика, если это событие от только что сохраненной модели
        if source != ALERT_COUNTER:
            with AlertService(init_by=source) as service:
                _new_counter_value = event.value
                if event.change == "set":
                    service.set_alert_counter(value=event.value, comment=event.comment)
                else:
                    is_increased = event.change != "decrease"
                    service.change_alert_counter(value=event.value, increase=is_increased, comment=event.comment)
                    _new_counter_value = service.get_last_counter()
                # изменяем уровень тревоги, если счетчик попадает в диапазон срабатывания
                new_state = service.get_state_by_alert(_new_counter_value)
                old_state = service.get_state_current()
                if new_state and new_state != old_state:
                    # новое ALERT_STATE событие, которое отправит конфиги,
                    # будет создано моделью AlertState при сохранении в этой процедуре
                    service.set_state_current(new_state)  # заканчиваем обработку
                    self.add_log_event(
                        f"alert state switched from {old_state} to {new_state} by counter",
                        level=ContextEventLevels.LOG,
                    )

        # В случае, когда событие инициировано ALERT_STATE апдейт для шкалы уже был отправлен
        if source == ALERT_COUNTER:
            with AlertService(init_by=source) as service:
                current_state = service.get_state_current()
                new_state = service.get_state_by_alert(event.value)
                if new_state != current_state:
                    service.set_state_current(new_state)
                    self.add_log_event(
                        f"alert state switched from {old_state} to {new_state} by counter", level=ContextEventLevels.LOG
                    )
            # при изменениях параметра счетчика апдейт отправляется только шкалам
            with get_interface() as publisher:
                publisher.publish(
                    body={},
                    exchange=publisher.config.exchanges.get("internal"),
                    routing_key=format_routing_key(SkabenQueue.CLIENT_UPDATE.value, SkabenTopics.SCL, "all"),
                )

    def apply(self, event_headers: dict, event_data: dict):
        """Корневой обработчик событий, связанных с тревогой.

        Валидирует данные, принятые из очереди в соответствии с моделью события.
        """

        event_type = event_headers.get("event_type", "")
        event_class = self.event_types.get(event_type)
        if not event_class:
            return event_headers, event_data

        _data = event_class.decode(event_headers=event_headers, event_data=event_data)
        event = event_class.model_validate(_data)

        if event.event_type == ALERT_STATE:
            self._handle_alert_state_event(event)

        if event.event_type == ALERT_COUNTER:
            self._handle_alert_counter_event(event)

        return event_headers, event_data

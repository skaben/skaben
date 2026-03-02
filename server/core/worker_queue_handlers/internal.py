import logging
from typing import Dict, List


from pydantic import ValidationError
from core.transport.publish import get_interface
from core.transport.events import SkabenEvent, SkabenLogEvent
from core.transport.config import MQConfig, SkabenQueue
from core.transport.packets import SkabenPacketTypes
from event_contexts.device.events import SkabenDeviceEvent
from streams.models import StreamRecord, StreamTypes
from core.worker_queue_handlers.base import BaseHandler
from event_contexts.alert.context import AlertEventContext as alert_context
from event_contexts.device.context import DeviceEventContext as device_context
from kombu import Message

# TODO: разделить сущность на роутер и обработчика событий.
# в текущей реализации нарушается принцип single responsibility


class InternalHandler(BaseHandler):
    """Обработчик внутренней очереди."""

    name: str = "main_internal"

    incoming_mark: str = SkabenQueue.INTERNAL.value

    state_save_queue_mark: str = SkabenQueue.STATE_UPDATE.value
    client_update_queue_mark: str = SkabenQueue.CLIENT_UPDATE.value

    state_save_packet_mark: str = SkabenPacketTypes.SUP
    client_update_packet_mark: str = SkabenPacketTypes.CUP
    info_packet_mark: str = SkabenPacketTypes.INFO
    keepalive_packet_mark: str = SkabenPacketTypes.PONG

    def __init__(self, config: MQConfig, queues: Dict[str, str]):
        super().__init__(config, queues)

    def handle_message(self, body: Dict, message: Message) -> None:
        """Распознает внутренние сообщения в зависимости от заголовков.

        Args:
            body (dict): Тело сообщения.
            message (Message): Экземпляр сообщения.
        """
        try:
            if message.headers and message.headers.get("event_type"):
                # сообщение является событием внутренней очереди и должно быть обработано
                self.handle_event(message.headers, body)
            else:
                # пакеты не обладают заголовком event_type и отправляются в метод-роутер
                self.route_message(body, message)
        except Exception:  # noqa
            logging.exception(f"while handling internal queue message {message.headers} {message}")

        if not message.acknowledged:
            message.ack()

    def handle_event(self, event_headers: dict, event_data: dict):
        """Обрабатывает события на основе типа события и данных.

        Это основная функция-обработчик, здесь применяются сценарии игры.

        Аргументы:
            headers (dict): Мета-данные события, включающие тип.
            event_data (dict): Полезная нагрузка события.
        """
        events = []
        if SkabenLogEvent.has_event_type(event_headers.get("event_type")):
            log_event = SkabenLogEvent.from_event_data(event_headers, event_data)
            if log_event.save:
                return self.handle_context_events([log_event])

        for context in [
            alert_context,
            device_context,
        ]:
            with context() as ctx:
                ctx.apply(event_headers, event_data)
                events.extend(ctx.events)
        self.handle_context_events(events)

    @staticmethod
    def handle_context_events(events: List[SkabenEvent]):
        """Обработка событий, возникших в процессе выполнения контекста.

        Все события с типом log отправляются в выделенный stream RabbitMQ.
        Все события иных типов - повторно добавляются в очередь internal для обработки.
        """
        save_as_records = []
        send_as_events = []
        for event in events:
            if event.has_event_type("log"):
                try:
                    record = StreamRecord(
                        message=event.message,
                        message_data=event.message_data,
                        stream=StreamTypes.LOG,
                        source=event.event_source,
                        mark=event.level,
                    )
                    save_as_records.append(record)
                except Exception:  # noqa
                    logging.exception("cannot create stream record:")
                    continue
            else:
                send_as_events.append(event)

        if save_as_records:
            StreamRecord.objects.bulk_create(save_as_records)
        if send_as_events:
            with get_interface() as publisher:
                [publisher.send_event(event) for event in send_as_events]

    def route_message(self, body: Dict, message: Message) -> None:
        """Перенаправляет события в различные очереди, в зависимости от типа пакета.

        Args:
            body (dict): Тело сообщения.
            message (Message): Экземпляр сообщения.
        """
        try:
            routing_key = message.delivery_info.get("routing_key")
            _routing_data = dict(enumerate(routing_key.split(".")))

            if len(_routing_data.keys()) < 4:
                logging.error("bad packet routing key: %s", routing_key)
                return message.reject()

            incoming_mark = _routing_data.get(0)
            device_type = _routing_data.get(1)
            device_uid = _routing_data.get(2)
            packet_type = _routing_data.get(3)
            if incoming_mark != self.incoming_mark:
                return message.requeue()
        except ValueError:
            logging.exception("cannot handle internal queue message")
            return message.reject()

        # todo: здесь пакет должен терминироваться и превращаться в SkabenEvent

        if packet_type == self.state_save_packet_mark:
            self.dispatch(data=body["datahold"], routing_data=[self.state_save_queue_mark, device_type, device_uid])
            return message.ack()

        if packet_type == self.client_update_packet_mark:
            self.dispatch(data=body, routing_data=[self.client_update_queue_mark, device_type, device_uid])
            return message.ack()

        # INFO-пакеты не переадресуются и обрабатываются здесь.
        if packet_type == self.info_packet_mark:
            # происходит конвертация INFO пакета в событие внутренней очереди.
            try:
                internal_event = SkabenDeviceEvent(
                    event_type="device",
                    event_source="mqtt",
                    device_type=device_type,
                    device_uid=device_uid,
                    payload=body.get("datahold", {}),
                )
                encoded = internal_event.encode()
                self.handle_event(encoded.headers, encoded.data)
            except ValidationError:
                logging.exception("While validating INFO message from device:")
                return message.reject()
        else:
            return message.reject()

        if not message.acknowledged:
            return message.ack()

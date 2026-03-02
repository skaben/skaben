"""Описывает работу обработчика для ask exchange - входящих MQTT пакетов."""

import logging
from typing import Dict, Union

from django.conf import settings

from core.helpers import from_json, get_server_timestamp
from core.models.base import DeviceKeepalive
from core.transport.config import MQConfig, SkabenQueue
from core.transport.packets import SkabenPacketTypes
from core.worker_queue_handlers.base import BaseHandler
from kombu import Message

# TODO: применить здесь систему SkabenEvent


class AskHandler(BaseHandler):
    """Конвертирует входящие сообщения из MQTT в сообщения внутренней очереди."""

    name: str = "mqtt_bridge_ask_handler"
    incoming_mark: str = SkabenQueue.ASK.value
    outgoing_mark: str = SkabenQueue.INTERNAL.value
    datahold_packet_mark: list[str] = [SkabenPacketTypes.INFO, SkabenPacketTypes.CUP, SkabenPacketTypes.SUP]

    def __init__(self, config: MQConfig, queues: Dict[str, str]):
        """
        Initializes the TranslatorHandler.

        Args:
            config (MQConfig): The message queue configuration.
            queues (dict): The queues for the handler.
        """
        super().__init__(config, queues)

    def handle_message(self, body: Union[str, Dict], message: Message) -> None:
        """
        Handles incoming messages.

        Args:
            body (Union[str, Dict]): The message body.
            message (Message): The message instance.
        """
        try:
            routing_key = message.delivery_info.get("routing_key")
            _routing_data = dict(enumerate(routing_key.split(".")))

            if len(_routing_data.keys()) < 4:
                logging.error("bad packet routing key: %s", routing_key)
                return message.reject()

            routing_type = _routing_data.get(0)
            device_type = _routing_data.get(1)
            device_uid = _routing_data.get(2)
            packet_type = _routing_data.get(3)
            if routing_type != self.incoming_mark:
                return message.requeue()
        except ValueError:
            logging.exception("cannot handle message routing key")
            return message.reject()

        try:
            payload_data = from_json(body)
            _timestamp = payload_data.get("timestamp", 0)
            timestamp, is_online = self.keepalive_status(device_uid, _timestamp)

            if packet_type in self.datahold_packet_mark:
                payload_data.update(self.parse_datahold(payload_data))

            if not is_online:
                # Любой пакет от устройства с просроченным timestamp будет отброшен
                # Вместо ответа на пакет сервер посылает текущий конфиг устройства
                self.dispatch(
                    data={},
                    routing_data=[self.outgoing_mark, device_type, device_uid, SkabenPacketTypes.CUP],
                )
                return message.ack()
        except Exception:
            logging.exception("cannot parse message payload")
            return message.reject()

        self.dispatch(
            data=payload_data,
            routing_data=[self.outgoing_mark, device_type, device_uid, packet_type],
        )
        if not message.acknowledged:
            message.ack()

    @staticmethod
    def get_simple_keepalive(timestamp: int) -> [int, bool]:
        if timestamp + settings.KEEPALIVE_INTERVAL > get_server_timestamp():
            return timestamp, True
        else:
            return get_server_timestamp(), False

    @staticmethod
    def keepalive_status(mac_addr: str, timestamp: int) -> [int, bool]:
        if mac_addr == "all":
            timestamp = get_server_timestamp()
            return timestamp, True

        try:
            keepalive = DeviceKeepalive.objects.get(mac_addr=mac_addr)
            result = timestamp, keepalive.online
            keepalive.timestamp = timestamp
            keepalive.save()
        except DeviceKeepalive.DoesNotExist:
            timestamp = get_server_timestamp()
            DeviceKeepalive.objects.create(timestamp=timestamp, mac_addr=mac_addr)
            result = timestamp, False
        return result

    @staticmethod
    def parse_datahold(data: Union[str, Dict]) -> Dict:
        """
        Parses datahold from a message.

        Args:
            data (Union[str, Dict]): The message data.

        Returns:
            The parsed datahold.
        """
        result = {"datahold": f"{data}"}
        if isinstance(data, dict):
            result = dict(
                timestamp=int(data.get("timestamp", 0)),
                task_id=data.get("task_id", 0),
                hash=data.get("hash", ""),
                datahold=from_json(data.get("datahold", {})),
            )
        return result

import logging
from typing import Dict

from core.models import DeviceTopic
from core.transport.config import MQConfig, SkabenQueue
from core.transport.publish import get_interface
from core.transport.topics import get_topics, SkabenTopics
from core.worker_queue_handlers.base import BaseHandler
from event_contexts.device.lock_access_context import LockEventContext
from kombu import Message
from peripheral_devices.models.lock import LockDevice
from peripheral_devices.service.packet_format import cup_packet_from_smart, cup_packet_from_simple
from peripheral_devices.service.passive_config import get_passive_config
from peripheral_devices.models.helpers import get_model_by_topic


class ClientUpdateHandler(BaseHandler):
    """
    Handler for incoming client update messages.

    Attributes:
        incoming_mark (str): The incoming message mark.
    """

    name: str = "client_updater"
    incoming_mark: str = SkabenQueue.CLIENT_UPDATE.value

    def __init__(self, config: MQConfig, queues: Dict[str, str]):
        """
        Initializes the ClientUpdateHandler.

        Args:
            config (MQConfig): The message queue configuration.
            queues (dict): The queues for the handler.
        """
        super().__init__(config, queues)
        self.all_topics = get_topics()

    def handle_message(self, body: Dict, message: Message) -> None:
        """Обрабатывает входящее сообщение."""
        try:
            routing_key = message.delivery_info.get("routing_key")
            _routing_data = dict(enumerate(routing_key.split(".")))
            incoming_mark = _routing_data.get(0)
            device_topic = _routing_data.get(1)
            device_uid = None
            if incoming_mark != self.incoming_mark:
                return message.requeue()
            if len(_routing_data) > 2:
                device_uid = _routing_data.get(2)
        except ValueError:
            logging.exception("cannot handle client update message")
            return message.reject()
        if device_topic not in DeviceTopic.objects.get_topics_active():
            return message.ack()

        try:
            if device_topic not in DeviceTopic.objects.get_topics_permitted():
                logging.error(f"Client update wasn't handled. Unknown device `{device_topic}`")
                return message.reject()

            if device_topic in DeviceTopic.objects.get_topics_by_type("simple"):
                data = get_passive_config(device_topic)
                if data:
                    packet = cup_packet_from_simple(topic=device_topic, payload=data, mac_addr=device_uid)
                    with get_interface() as interface:
                        interface.send_mqtt(packet)
                return message.ack()

            if device_topic in DeviceTopic.objects.get_topics_by_type("smart"):
                targets = []
                model = get_model_by_topic(device_topic)
                if device_uid == "all":
                    targets = list(model.objects.not_overridden())
                if device_uid and device_uid != "all":
                    targets = [self.get_device_instance(device_topic, device_uid, body, message)]
                for target in targets:
                    with get_interface() as publisher:
                        packet = cup_packet_from_smart(target)
                        publisher.send_mqtt(packet)

        except Exception as e:  # noqa
            self.send_log(str(e), level="error")
            logging.exception("Exception while handling client update.")
            return message.reject()

        if not message.acknowledged:
            return message.ack()

    def get_device_instance(self, device_topic: str, device_uid: str, body: dict, message: Message):
        """Получает актуальную конфигурацию устройства."""
        model = get_model_by_topic(device_topic)
        try:
            instance = model.objects.get(mac_addr=device_uid)
            if instance.override:
                logging.warning(f"device {device_uid} is under override policy. skipping update")
                return
            if message.headers.get("force_update") or instance.get_hash() != body.get("hash", 1):
                return instance
        except model.DoesNotExist:
            return self._create_missing_devices(device_topic, device_uid)

    def _create_missing_devices(self, device_topic: str, device_uid: str):
        try:
            if device_topic == SkabenTopics.LOCK:
                with LockEventContext() as context:
                    message = context.create_lock_device(device_uid)
                    self.send_log(message)
                    return LockDevice.objects.get(mac_addr=device_uid)
        except Exception as e:
            self.send_log(str(e), level="error")

import logging
from typing import Dict

from core.models.mqtt import DeviceTopic
from core.transport.config import MQConfig, SkabenQueue
from core.worker_queue_handlers.base import BaseHandler
from kombu import Message
from peripheral_devices.models.helpers import get_model_by_topic


class StateUpdateHandler(BaseHandler):
    """
    Handler for state update messages.
    """

    name: str = "state_update"
    incoming_mark: str = SkabenQueue.STATE_UPDATE.value

    def __init__(self, config: MQConfig, queues: Dict[str, str]):
        """
        Initializes the StateUpdateHandler.

        Args:
            config (MQConfig): The message queue configuration.
            queues (dict): The queues for the handler.
        """
        super().__init__(config, queues)

    def handle_message(self, body: Dict, message: Message) -> None:
        """
        Handles incoming state update messages.

        Args:
            body (dict): The message body.
            message (Message): The message instance.
        """
        try:
            routing_data = message.delivery_info.get("routing_key").split(".")
            [incoming_mark, device_topic, device_uid] = routing_data
            if incoming_mark != self.incoming_mark:
                return message.requeue()
        except ValueError:
            logging.exception("cannot handle state update message")
            return message.reject()

        if device_topic not in DeviceTopic.objects.get_topics_by_type("smart"):
            return message.reject()
        model = get_model_by_topic(device_topic)
        if not model:
            logging.error("uknown device %s", device_topic)

        try:
            parsed_data = model.from_mqtt_config(body)
            model.objects.filter(mac_addr=device_uid).update(**parsed_data)
        except model.DoesNotExist:
            # todo: dispatch "device_not_found" event
            logging.error("%s does not exists", str(model))
            pass

        if not message.acknowledged:
            message.ack()

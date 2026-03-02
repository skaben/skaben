from typing import List

import logging
import time
from enum import Enum

from dataclasses import dataclass

import kombu
from django.conf import settings
from kombu import Connection, Exchange, Queue
from kombu.pools import connections
from kombu.exceptions import OperationalError

kombu.disable_insecure_serializers(allowed=["json"])


def get_connection():
    return Connection(settings.AMQP_URI, transport_options={"confirm_publish": True})


# todo: rewrite as dataclass
class SkabenQueue(Enum):
    ASK = "ask"  # incoming mqtt packets (todo: check is it correct place for 'ask' queue? it is not internal)
    STATE_UPDATE = "state_update"  # update configuration server-side
    CLIENT_UPDATE = "client_update"  # update configuration client-side
    INTERNAL = "internal"  # marking as internal event


@dataclass(frozen=True)
class SkabenRecurrentTasks:
    PING: str = "ping"
    ALERT_CHANGE: str = "alert_change"

    @property
    def allowed(self) -> List[str]:
        return [self.PING, self.ALERT_CHANGE]


class MQFactory:
    @staticmethod
    def create_queue(queue_name: str, exchange: Exchange, is_topic: bool = True, **kwargs) -> Queue:
        routing_key = queue_name if not is_topic else f"{queue_name}.#"
        return Queue(queue_name, exchange=exchange, routing_key=routing_key, **kwargs)

    @staticmethod
    def create_exchange(channel, name: str, routing_type: str):
        exchange = Exchange(name, routing_type)
        bound_exchange = exchange(channel)
        return bound_exchange


class MQConfig:
    exchanges: dict
    queues: dict
    _exchanges_initialized: bool

    def __init__(self):
        if not settings.AMQP_URI:
            raise AttributeError("CRIT: settings.AMQP_URI is missing, exchanges will not be initialized")

        self.queues = {}
        self.exchanges = {}
        self._exchanges_initialized = False

    def init_exchanges_and_queues(self, max_retries=30, retry_delay=2):
        """Initialize exchanges and queues with exponential backoff retry logic.
        
        Should be called after connection to RabbitMQ is established.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
        """
        if self._exchanges_initialized:
            return

        logging.info("Initializing exchanges and queues")
        
        for attempt in range(max_retries):
            try:
                self._exchanges_initialized = self.on_broker_ready()
            except OperationalError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** min(attempt, 5))  # Cap exponential backoff at 2^5
                    logging.warning(
                        f"Failed to connect to RabbitMQ (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s... Error: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logging.error(f"Failed to initialize exchanges after {max_retries} attempts")
                    raise

    def on_broker_ready(self) -> bool:
        self._init_mqtt_exchange()
        self._init_internal_exchange()

        filtering_queue = {
            settings.ASK_QUEUE: MQFactory.create_queue(settings.ASK_QUEUE, self.mqtt_exchange, durable=True)
        }
        transport_queues = {
            e.value: MQFactory.create_queue(e.value, self.internal_exchange, durable=True) for e in SkabenQueue
        }
        queues_full = transport_queues | filtering_queue
        self.bind_queues(queues=queues_full)
        self.queues = queues_full
        return True

    @property
    def internal_exchange(self) -> Exchange:
        if "internal" not in self.exchanges:
            self._init_internal_exchange()
        return self.exchanges.get("internal")

    @property
    def mqtt_exchange(self) -> Exchange:
        if "mqtt" not in self.exchanges:
            self._init_mqtt_exchange()
        return self.exchanges.get("mqtt")

    def bind_queues(self, queues):
        conn = get_connection()
        with connections[conn].acquire(block=True) as pool:
            for queue in queues.values():
                bound_queue = queue(pool)
                bound_queue.declare()

    def _init_mqtt_exchange(self) -> Exchange:
        """Initialize MQTT exchange infrastructure"""
        if "mqtt" in self.exchanges:
            return self.exchanges["mqtt"]

        logging.info("initializing mqtt exchange")
        conn = get_connection()
        with connections[conn].acquire(block=True) as pool:
            exchange = MQFactory.create_exchange(pool, "mqtt", "topic")
            self.exchanges.update(mqtt=exchange)
            return exchange

    def _init_internal_exchange(self) -> Exchange:
        """Initializing internal exchange"""
        if "internal" in self.exchanges:
            return self.exchanges["internal"]

        logging.info("initializing internal exchange")
        conn = get_connection()
        with connections[conn].acquire(block=True) as pool:
            exchange = MQFactory.create_exchange(pool, "internal", "topic")
            self.exchanges.update(internal=exchange)
            return exchange

    def __str__(self):
        return (
            f"<MQConfig exchanges: "
            f"{','.join(list(self.exchanges.keys()))} | "
            f"queues: {','.join(list(self.queues.keys()))}>"
        )


def get_mq_config() -> MQConfig:
    return MQConfig()

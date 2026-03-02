import logging

from core.transport.config import MQConfig, SkabenQueue, get_connection, get_mq_config
from core.transport.packets import SkabenPacket
from core.transport.events import SkabenEvent
from kombu.pools import producers


def publish(body, exchange, routing_key, **kwargs):
    body = body or {}
    conn = get_connection()
    try:
        with producers[conn].acquire(block=True) as prod:
            prod.publish(
                body=body, exchange=exchange, declare=[exchange], routing_key=routing_key, retry=True, **kwargs
            )
    except Exception as e:
        logging.error(f"[sync] exception occurred when sending packet to {routing_key}: {e}")


class MQPublisher(object):
    """Паблишер для очередей. Предназначен для использования другими модулями."""

    def __init__(self, config: MQConfig):
        self.config = config

    def send_mqtt(self, packet: SkabenPacket):
        """Отправить SKABEN пакет через MQTT"""
        return publish(body=packet.encode(), exchange=self.config.exchanges.get("mqtt"), routing_key=packet.routing_key)

    def send_event(self, event: SkabenEvent):
        """Отправляет событие с заголовками."""
        encoded = event.encode()

        return publish(
            body=encoded.data,
            headers=encoded.headers,
            exchange=self.config.exchanges.get("internal"),
            routing_key=f"{SkabenQueue.INTERNAL.value}",
        )

    @staticmethod
    def publish(body, exchange, routing_key, **kwargs):
        """Метод-обертка для publish."""
        return publish(body, exchange, routing_key, **kwargs)

    def __str__(self):
        return f'<MQPublisher ["config": {self.config}]>'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return


def get_interface():
    return MQPublisher(get_mq_config())

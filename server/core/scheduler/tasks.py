from core.models.mqtt import DeviceTopic
from core.transport.packets import PING
from core.transport.publish import get_interface
from event_contexts.alert.tasks import create_alert_auto_event
from core.scheduler.types import SkabenTaskType
from core.tasks import update_devices


class SkabenTask:
    """Абстрактный класс задач для Планировщика."""

    name: str
    timeout: int
    requeue: bool

    def __init__(self, timeout: int, requeue: bool = False):
        self.timeout = timeout
        self.requeue = requeue

    def run(self):
        raise NotImplementedError


class PingerTask(SkabenTask):
    """Отправляет пакеты PING в каждый активный MQTT топик."""

    name: str = SkabenTaskType.PINGER

    def __init__(self, timeout: int, requeue: bool):
        super().__init__(timeout, requeue)

    def run(self) -> int:
        with get_interface() as publisher:
            for topic in DeviceTopic.objects.get_topics_active():
                packet = PING(topic=topic)
                publisher.send_mqtt(packet)
        return self.timeout


class AlertTask(SkabenTask):
    """Отслеживает состояние уровня тревоги и изменяет счетчик тревоги."""

    name: str = SkabenTaskType.ALERT

    def __init__(self, timeout: int, requeue: bool):
        super().__init__(timeout, requeue)

    def run(self) -> int:
        event, timeout = create_alert_auto_event()
        if event:
            with get_interface() as publisher:
                publisher.send_event(event)
        return timeout


class UpdateDevicesOnStartTask(SkabenTask):
    name: str = SkabenTaskType.UPDATE_DEVICE

    def __init__(self, timeout: int = 0, requeue: bool = False):
        super().__init__(timeout, requeue)

    def run(self):
        update_devices(["all"])
        return 0

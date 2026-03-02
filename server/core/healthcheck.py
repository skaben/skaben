from dataclasses import dataclass
from typing import List, Literal

from alert.models import AlertState
from alert.service import AlertService
from core.exceptions import ConfigException
from core.models import ControlReaction, DeviceTopic
from peripheral_behavior.models.access import SkabenUser
from core.transport.config import SkabenQueue, get_mq_config
from django.conf import settings


@dataclass(frozen=True)
class IntegrationModules:
    DATABASE: str = "DATABASE"
    REDIS_CACHE: str = "REDIS_CACHE"
    BROKER_QUEUES: str = "BROKER_QUEUES"
    ALERT_STATE: str = "ALERT_STATE"
    ALERT_COUNTER: str = "ALERT_COUNTER"
    DEVICE_CHANNELS: str = "DEVICE_CHANNELS"
    ACCESS_CONTROL: str = "ACCESS_CONTROL"


class IntegrityCheck:
    _status = Literal["ok", "error"]
    errors: List[str]
    messages: List[str]

    def __init__(self) -> None:
        self.errors = []
        self.messages = []

    @property
    def ok(self):
        if self.errors and len(self.errors) > 0:
            return False
        return True

    def run(self):
        try:
            self._check()
        except Exception as e:
            self.errors.append(str(e))

    def _check(self):
        raise NotImplementedError("method should be called only from inherited classes")


class AlertCounterIntegrityCheck(IntegrityCheck):
    """Проверяет и создает последний счетчик, если его нет."""

    def _check(self):
        with AlertService() as service:
            service.get_last_counter()


class AlertStateIntegrityCheck(IntegrityCheck):
    """Проверяет наличие уровней тревоги и выбранный текущий уровень."""

    def _check(self):
        with AlertService() as service:
            try:
                # это проверит, назначен ли текущий уровень тревоги
                service.get_state_current()
            except AlertState.DoesNotExist:
                existing_states = AlertState.objects.all().order_by("order")
                if existing_states.count() == 0:
                    raise ConfigException("Alert States not configured, load initial data from .json to fix it")
                service.set_state_current(existing_states[0])


class DeviceIntegrityCheck(IntegrityCheck):
    def _check(self):
        try:
            active_topics = DeviceTopic.objects.filter(active=True).values_list("channel", flat=True)
            reaction_count = ControlReaction.objects.count()
            self.messages = [f"Active MQTT topics:\t{list(active_topics)}", f"Custom MQTT reactions:\t{reaction_count}"]
        except Exception:
            raise ConfigException(
                "Device topics misconfigured, check settings.SKABEN_DEVICE_TOPICS and DB MqttTopics content"
            )


class AccessControlIntegrityCheck(IntegrityCheck):
    def _check(self):
        try:
            SkabenUser.objects.get_or_create(name="skaben_default", description="системный пользователь по умолчанию")
        except Exception:
            raise ConfigException("Default skaben user cannot be added")


class BrokerIntegrityCheck(IntegrityCheck):
    def _check(self):
        config = get_mq_config()
        if not config.internal_exchange or not config.mqtt_exchange:
            raise ConfigException("Exchange configuration mismatch")
        queues = sorted([e.value for e in SkabenQueue] + [settings.ASK_QUEUE])
        if sorted(config.queues) != queues:
            raise ConfigException("Queue configuration mismatch")


INTEGRATION_MODULE_MAP = {
    IntegrationModules.ALERT_STATE: AlertStateIntegrityCheck,
    IntegrationModules.ALERT_COUNTER: AlertCounterIntegrityCheck,
    IntegrationModules.DEVICE_CHANNELS: DeviceIntegrityCheck,
    IntegrationModules.ACCESS_CONTROL: AccessControlIntegrityCheck,
}

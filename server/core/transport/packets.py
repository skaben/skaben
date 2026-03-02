from dataclasses import dataclass
from typing import Optional

from core.helpers import format_routing_key, get_server_timestamp
from pydantic import BaseModel, Field, computed_field


@dataclass(frozen=True)
class SkabenPacketTypes:
    PING: str = "ping"
    PONG: str = "pong"
    ACK: str = "ack"
    NACK: str = "nack"
    INFO: str = "info"
    CUP: str = "cup"
    SUP: str = "sup"


class SkabenPacket(BaseModel):
    """Абстрактный класс пакета.

    В отличие от События (SkabenEvent), предназначен для общения с периферийными устройствами
    посредством MQTT (отдельный exchange в RabbitMQ)
    """

    uid: str = "all"  # по умолчанию броадкаст
    topic: str = Field(description="Device type")
    command: str = Field(description="Packet type")
    timestamp: int = Field(default_factory=get_server_timestamp)

    @computed_field(return_type=str)
    @property
    def routing_key(self) -> str:
        """Вычисляемое поле, определяющее куда будет отправлен пакет."""
        return format_routing_key(self.topic, self.uid, self.command)

    def encode(self):
        """Подготавливает содержимое для отправки в очередь MQTT."""
        return self.model_dump_json(exclude={"topic", "uid", "command", "routing_key"}, exclude_none=True)


class PING(SkabenPacket):
    """PING пакет. По умолчанию отправляется всем."""

    command: str = SkabenPacketTypes.PING

    def encode(self):
        """Подготавливает содержимое для отправки в очередь MQTT."""
        return self.model_dump_json(include={"timestamp"})


class ACK(SkabenPacket):
    """Подтверждает операцию как успешную."""

    command: str = SkabenPacketTypes.ACK


class NACK(SkabenPacket):
    """Подтверждает операцию как не-успешную."""

    command: str = SkabenPacketTypes.NACK


class DataholdPacket(SkabenPacket):
    """Расширенный абстрактный пакет, включающий в себя полезную нагрузку."""

    datahold: dict = {}  # packet data load

    def __init__(
        self,
        topic: str,
        datahold: dict,
        timestamp: int,
        config_hash: Optional[str] = None,
        uid: Optional[str] = None,
        task_id: Optional[str] = None,
    ):
        super().__init__(topic=topic, timestamp=timestamp, config_hash=config_hash, uid=uid)
        self.datahold = datahold
        self.task_id = task_id


class INFO(DataholdPacket):
    """INFO пакет предназначен для отправки событий от клиентов, которые
    не затрагивают напрямую изменение конфигурации устройства.

    В это входит апдейт счетчиков тревоги, программируемые игровые события, и т.д.
    """

    command: str = SkabenPacketTypes.INFO
    task_id: Optional[str] = None


class SUP(DataholdPacket):
    """SUP пакет - отправляется клиентом, чтобы сообщить об изменении его конфигурации серверу."""

    command: str = SkabenPacketTypes.SUP
    task_id: Optional[str] = None


class CUP(DataholdPacket):
    """CUP пакет - два сценария использования:

    1. Как правило - отправляется сервером для доставки конфигурации клиенту.
    2. Реже - может быть отправлен со стороны клиента для срочного запроса своей конфигурации.
    """

    command: str = SkabenPacketTypes.CUP
    task_id: Optional[str] = None
    config_hash: Optional[str] = ""

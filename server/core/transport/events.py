from typing import Dict, Optional, Union, List, Literal, ClassVar

from dataclasses import dataclass

from pydantic import BaseModel as PydanticBaseModel
from pydantic_core import from_json


class BaseModel(PydanticBaseModel):
    class Config:
        arbitrary_types_allowed = True


class EncodedEvent(BaseModel):
    """Событие, готовое к отправке во внутреннюю очередь."""

    headers: Optional[Dict[str, str | int | bool]]
    data: Optional[Dict[str, Union[str, int, bool, dict, list]]]


class SkabenEvent(BaseModel):
    """Базовый внутренний эвент (событие).

    Определяет структуру для различных событий, происходящих внутри приложения (очередь internal).

    Атрибуты:
        event_type (str): Тип события. В соответствии с ним выполняется обработка события роутером.
        event_source (str): Источник события. Это указывает на систему или компонент, который сгенерировал событие. Значение по умолчанию: "default"
        message (str): Дополнительное сообщение, связанное с событием.
        save (bool): Определяет, нужно ли сохранить сообщение в БД.
    """

    _event_type: ClassVar[str] = "change_me"  # todo: merge with event_type
    event_type: str = "change_me"
    event_source: str = "default"

    def encode(self) -> EncodedEvent:
        """Подготавливает данные события для отправки во внутреннюю очередь.

        Возвращает тип события для включения в заголовок сообщения очереди и полезную нагрузку события."""
        headers_data = {key: getattr(self, key) for key in self.headers}
        event = EncodedEvent(headers=headers_data, data=self.model_dump(exclude={*self.headers}))
        return event

    @property
    def headers(self) -> List[str]:
        """Возвращает список заголовков события."""
        return ["event_type", "event_source"]

    @staticmethod
    def decode(event_headers: dict, event_data: Union[str, dict]) -> dict:
        """Подготавливает данные к валидации моделью."""
        if isinstance(event_data, dict):
            _converted_event_data = event_data
        else:
            _converted_event_data = from_json(event_data)

        return {
            "event_type": event_headers.get("event_type", ""),
            "event_source": event_headers.get("event_source", ""),
            **_converted_event_data,
        }

    @classmethod
    def from_event_data(cls, event_headers: dict, event_data: Union[str, dict]) -> Optional["SkabenEvent"]:
        if cls.has_event_type(event_type=event_headers.get("event_type", "")):
            decoded = cls.decode(event_headers, event_data)
            return cls(**decoded)

    @classmethod
    def has_event_type(cls, event_type: str):
        return cls._event_type == event_type


@dataclass(frozen=True)
class ContextEventLevels:
    LOG: Literal["log"] = "log"
    ERROR: Literal["error"] = "error"
    INFO: Literal["info"] = "info"


# todo: move to streams
class SkabenLogEvent(SkabenEvent):
    """Событие внутри контекста, требующее логирования."""

    _event_type: ClassVar[str] = "log"
    event_type: str = "log"
    event_source: str
    level: Literal["error", "log", "info"] = ContextEventLevels.INFO
    message: str
    message_data: Optional[Dict[str, Union[str, int, bool, dict, list]]]
    save: bool = True

    @property
    def headers(self) -> List[str]:
        return super().headers + ["level"]

    def __str__(self):
        return f"[{self.level}] save: {self.save} | {self.message}"


class SkabenEventContext:
    """Базовый контекст обработчика событий."""

    events: List[SkabenEvent | SkabenLogEvent] = []

    def __init__(self):
        self.events = []

    def apply(self, event_headers: dict, event_data: dict):
        raise NotImplementedError("abstract class method")

    def add_log_event(
        self,
        message: str,
        level: Literal["error", "log", "info"] = ContextEventLevels.INFO,
        message_data: Optional[Dict[str, Union[str, int, bool, dict, list]]] = None,
    ) -> List[SkabenLogEvent]:
        event = SkabenLogEvent(
            message=message,
            message_data=message_data,
            event_source=self._get_context_name(),
            level=level,
        )
        self.events.append(event)
        return self.events

    def _get_context_name(self) -> str:
        return type(self).__name__.lower()

    def __enter__(self):
        self.events = []
        return self

    def __exit__(self, type, value, traceback):
        return

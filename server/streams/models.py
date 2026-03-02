from dataclasses import dataclass

from core.helpers import get_server_timestamp, get_time, get_uuid
from django.db import models


@dataclass(frozen=True)
class StreamTypes:
    GAME: str = "game"
    LOG: str = "log"


class StreamRecord(models.Model):
    """Stream event record."""

    class Meta:
        verbose_name = "Игровое событие"
        verbose_name_plural = "Игровые события"

    uuid = models.UUIDField(primary_key=True, editable=False, default=get_uuid)
    timestamp = models.IntegerField(default=get_server_timestamp)

    message = models.CharField(help_text="Название события")
    message_data = models.JSONField(blank=True, null=True, default=dict, help_text="Содержимое события")

    stream = models.CharField(default=StreamTypes.GAME, max_length=256, help_text="Поток события")
    source = models.CharField(default="default", max_length=256, help_text="Источник события")
    mark = models.CharField(blank=True, max_length=32, help_text="Дополнительный маркер события")

    @property
    def human_time(self):
        return get_time(self.timestamp).split(" ")[1]

    def __str__(self):
        return f"{get_time(self.timestamp)}:{self.stream}:{self.source}:{self.mark} > {self.message}"

from core.transport.topics import get_topics
from django.db import models

__all__ = ("PassiveConfig",)

SIMPLE_DEVICES = [(val, val) for val in get_topics().simple]


class PassiveConfig(models.Model):
    """
    Представляет конфигурацию пассивного устройства, такого как светильник, сирена или RGB LED.

    Поля:
    - config (JSONField): JSON-объект с конфигурацией устройства.
    - topic (CharField): Строка, представляющая канал MQTT устройства.
    - state (ForeignKey): Внешний ключ на объект AlertState, представляющий текущее состояние устройства.

    Уникальные ограничения:
    - state и topic: Пассивное устройство может иметь только одну конфигурацию на каждое состояние и канал.

    """

    class Meta:
        verbose_name = "Пассивное устройство"
        verbose_name_plural = "Пассивные устройства"
        unique_together = ("state", "topic")

    config = models.JSONField(default=dict, help_text="JSON-объект с конфигурацией устройства.")
    comment = models.CharField(max_length=256, blank=True, null=True)
    topic = models.CharField(choices=SIMPLE_DEVICES, blank=False, help_text="Канал MQTT.")
    state = models.ForeignKey(
        "alert.AlertState",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Внешний ключ на объект AlertState, представляющий текущее состояние данжа.",
    )

    def __str__(self):
        """
        Возвращает строковое представление объекта PassiveConfig.
        """
        state_name = "N/A"
        if self.state:
            state_name = self.state.name.upper()
        return f"{self.topic} конфигурация [{state_name}] {self.config}"

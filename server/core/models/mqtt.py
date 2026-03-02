from typing import List, Set

from core.helpers import get_uuid
from django.conf import settings
from django.db import models

__all__ = ("DeviceTopic", "ControlReaction")

ALL = "all"
SIMPLE = "simple"
SMART = "smart"


class DeviceTopicManager(models.Manager):
    special_topics = [ALL, SIMPLE, SMART]

    def get_topics_active(self) -> List[str]:
        return list(self.get_queryset().filter(active=True).values_list("channel", flat=True))

    def get_topics_permitted(self) -> Set[str]:
        return set(list(self.get_queryset().values_list("channel", flat=True)) + self.special_topics)

    def get_topics_smart(self) -> List[str]:
        return self.get_topics_by_type(SMART)

    def get_topics_simple(self) -> List[str]:
        return self.get_topics_by_type(SIMPLE)

    def get_topics_by_type(self, _type: str) -> List[str]:
        permitted = self.get_topics_permitted()
        if _type not in permitted:
            ValueError(f"Invalid device type. Choose from {list(permitted)}.")
        if _type == ALL:
            qs = self.get_queryset().all()
        else:
            qs = self.get_queryset().filter(type=_type)
        return list(qs.values_list("channel", flat=True))


class DeviceTopic(models.Model):
    objects = DeviceTopicManager()

    class Meta:
        verbose_name = "MQTT устройство"
        verbose_name_plural = "MQTT устройства"

    TYPE_CHOICES = ((SIMPLE, "simple"), (SMART, "smart"))

    channel = models.CharField(max_length=settings.MAX_CHANNEL_NAME_LEN, unique=True, verbose_name="Канал MQTT")

    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=SIMPLE, verbose_name="Тип устройства")

    active = models.BooleanField(
        default=True,
        verbose_name="Активный топик",
        help_text="Выключение этого параметра останавливает обработку сообщений в этом канале",
    )

    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")

    def __str__(self):
        return f"<{self.channel}> - [{self.type} type] {self.comment}"


class ControlReaction(models.Model):
    """Управляющая команда"""

    uuid = models.UUIDField(primary_key=True, default=get_uuid, editable=False)

    name = models.CharField(
        verbose_name="Название команды", help_text="Должно быть уникальным", max_length=128, unique=True
    )

    payload = models.JSONField(verbose_name="Полезная нагрузка", help_text="Указывайте просто dict", default=dict)

    channel = models.ForeignKey(DeviceTopic, blank=True, null=True, on_delete=models.CASCADE)

    comment = models.TextField(verbose_name="Комментарий", default="", blank=True)

    routing = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name="Доп. параметры роутинга",
        help_text="Не трогайте это если не знаете что это",
    )

    exchange = models.CharField(
        max_length=settings.MAX_CHANNEL_NAME_LEN,
        choices=settings.EXCHANGE_CHOICES,
        default="mqtt",
        verbose_name="Выбор Exchange",
        help_text="Не трогайте это если не знаете что это",
    )

    @property
    def rk(self) -> str:
        """Actual routing key"""
        return f"{self.channel}.{self.routing}" if self.routing else self.channel

    def __str__(self):
        return f"Command {self.name} -> {self.comment[:64]}"

    class Meta:
        verbose_name = "MQTT: Реакция на команду"
        verbose_name_plural = "MQTT: Реакции на команду"

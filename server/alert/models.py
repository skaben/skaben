import logging

from core.exceptions import ConfigException
from core.transport.publish import get_interface
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from event_contexts.alert.events import (
    ALERT_COUNTER,
    ALERT_STATE,
    AlertCounterEvent,
    AlertStateEvent,
)


class AlertCounterManager(models.Manager):
    def create_initial(self, *args, **kwargs):
        initial_counter = self.model(value=0, comment="create initial")
        initial_counter.save(context="no_send")
        return initial_counter

    def get_latest(self):
        latest = self.get_queryset().latest("id")
        if not latest:
            latest = self.create_initial()
        return latest


class AlertCounter(models.Model):
    """Числовой счетчик уровня тревоги.

    При изменении до определенного уровня может вызывать переключения AlertState.
    Отображается на устройствах типа "шкала".
    """

    objects = AlertCounterManager()

    class Meta:
        verbose_name = "Тревога: счетчик уровня"
        verbose_name_plural = "Тревога: счетчик уровня"

    value = models.IntegerField(
        verbose_name="Значение счетчика",
        help_text="Счетчик примет указанное значение, уровень тревоги может быть сброшен",
        default=0,
    )
    comment = models.CharField(verbose_name="Причина изменений", default="reason: changed by admin", max_length=64)
    timestamp = models.DateTimeField(verbose_name="Время последнего изменения", default=timezone.now)

    def save(self, *args, **kwargs):
        """Сохранение, связывающее модели AlertCounter и AlertState."""
        source = ALERT_COUNTER

        if kwargs.get("event_source"):
            source = kwargs.pop("event_source")

        super().save(*args, **kwargs)
        if source != ALERT_STATE:
            with get_interface() as mq_interface:
                event = AlertCounterEvent(
                    value=self.value, event_source=ALERT_COUNTER, change="set", comment="self-generated"
                )
                mq_interface.send_event(event)

    def __str__(self):
        return f"{self.value} {self.comment} at {self.timestamp}"


class AlertStateManager(models.Manager):
    def get_current(self):
        try:
            return self.get_queryset().filter(current=True).get()
        except AlertState.DoesNotExist:
            raise ConfigException("current state is not set in DB")

    def get_ingame(self):
        return self.get_queryset().filter(ingame=True)

    def is_management_state(self):
        return self.get_queryset().filter(name="white", current=True).first()

    def is_lockdown_state(self):
        return self.get_queryset().filter(name="black", current=True).first()

    def is_pre_ignition_state(self):
        return self.get_queryset().filter(name="blue", current=True).first()

    def is_pre_power_state(self):
        return self.get_queryset().filter(name="cyan", current=True).first()


ALERT_INCREASE = "increase"
ALERT_DECREASE = "decrease"


class AlertState(models.Model):
    """Внутриигровой уровень тревоги.

    Управление уровнями тревоги переключает глобальное состояние системы.
    Отображается состоянием ламп\сирен (устройство типа "люстра").
    Может быть игровым и не-игровым, в игровом состоянии переключается изменением AlertCounter.
    """

    objects = AlertStateManager()

    AUTO_CHANGE_CHOICES = (
        (ALERT_INCREASE, "Увеличивать"),
        (ALERT_DECREASE, "Уменьшать"),
    )

    __original_state = None

    class Meta:
        verbose_name = "Тревога: именной статус"
        verbose_name_plural = "Тревога: именные статусы"

    name = models.CharField(verbose_name="Название статуса", max_length=32, blank=False, unique=True)
    info = models.CharField(verbose_name="Описание статуса", max_length=256)
    ingame = models.BooleanField(
        verbose_name="Игровой статус",
        help_text=(
            "Будет ли статус автоматически изменяться системой счетчика тревоги, "
            "или переключиться в него можно только специальным событием или вручную. "
        ),
        default=True,
    )
    threshold = models.IntegerField(
        verbose_name="Порог срабатывания ",
        help_text=(
            "Нижнее значение счетчика счетчика тревоги для переключения в статус. "
            "Чтобы отключить авто-переключение - выставьте значение ingame = False"
        ),
        default=-1,
    )
    current = models.BooleanField(verbose_name="Сейчас активен", default=False)
    order = models.IntegerField(
        verbose_name="Порядок",
        help_text="используется для идентификации и упорядочивания статуса без привязки к id в БД",
        blank=False,
        unique=True,
    )

    auto_change = models.CharField(
        choices=AUTO_CHANGE_CHOICES,
        verbose_name="Авто-изменение",
        help_text="Включить автоматическое повышение или понижение тревоги со временем",
        default=False,
    )

    auto_level = models.IntegerField(
        verbose_name="Значение авто-изменения",
        help_text="На сколько изменится уровень тревоги при авто-повышении или авто-понижении",
        default=0,
    )

    auto_timeout = models.IntegerField(
        verbose_name="Таймаут авто-изменения",
        help_text="Частота срабатывания авто-изменения уровня в секундах",
        default=0,
    )

    counter_increase = models.IntegerField(
        verbose_name="Значение увеличения",
        help_text="На сколько повысится уровень тревоги при ошибке игрока.",
        default=0,
    )

    counter_decrease = models.IntegerField(
        verbose_name="Значение уменьшения",
        help_text="На сколько снизится уровень тревоги при удачном действии игрока.",
        default=0,
    )

    def __init__(self, *args, **kwargs):
        super(AlertState, self).__init__(*args, **kwargs)
        self.__original_state = self.current

    @property
    def is_final(self):
        states = AlertState.objects.all().order_by("order")
        if len(states):
            return states.last().id == self.id  # type: ignore

    @property
    def get_current(self):
        if self.current:
            return self
        return AlertState.objects.all().filter(current=True).first()

    @staticmethod
    def get_by_name(name: str):
        return AlertState.objects.filter(name=name).first()

    def clean(self):
        has_current = AlertState.objects.all().exclude(pk=self.id).filter(current=True)
        if not self.current and not has_current:
            raise ValidationError("cannot unset current - no other current states")

    def save(self, *args, **kwargs):
        """Сохранение, связывающее модели AlertCounter и AlertState."""
        if self.current and not self.__original_state:
            other_states = AlertState.objects.all().exclude(pk=self.id)
            other_states.update(current=False)

        source = ALERT_STATE

        if kwargs.get("event_source"):
            source = kwargs.pop("event_source")

        super().save(*args, **kwargs)
        logging.debug(f"alert state changed to {self.name} [{self.order}]")

        if source != ALERT_COUNTER:
            counter_reset = source == ALERT_STATE
            if self.__original_state != self.current:
                with get_interface() as mq_interface:
                    event = AlertStateEvent(state=self.name, event_source=ALERT_STATE, counter_reset=counter_reset)
                    mq_interface.send_event(event)

        self.__original_state = self.current

    is_final.fget.short_description = "Финальный игровой статус"

    def __str__(self):
        active = "[active]" if self.current else ""
        return f"Уровень тревоги: {self.name} ({self.id}) {active}"

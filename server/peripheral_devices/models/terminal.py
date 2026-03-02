from typing import List

from django.db import models
from peripheral_devices.models.base import SkabenDevice, SkabenDeviceManager

__all__ = ("TerminalDevice",)


class TerminalDeviceManager(SkabenDeviceManager):
    """Менеджер терминалов.

    Все обновления вызываются через for для того, чтобы работал метод .save() модели
    """

    def set_blocked_all(self, value: bool):
        for terminal in self.objects.all():
            terminal.blocked = value
            terminal.save()

    def set_powered_all(self, value: bool):
        for terminal in self.objects.all():
            terminal.powered = value
            terminal.save()


class TerminalDevice(SkabenDevice):
    """Smart terminal."""

    objects = TerminalDeviceManager()

    class Meta:
        verbose_name = "Терминал"
        verbose_name_plural = "Терминалы"

    powered = models.BooleanField(default=False, verbose_name="Питание подключено")
    blocked = models.BooleanField(default=False, verbose_name="Устройство заблокировано")

    @property
    def topic(self) -> str:
        return "terminal"

    def get_related_accounts(self):
        menu_set = self.terminalmenuset_set.prefetch_related("state_id", "account")
        return [item.account for item in menu_set]

    def get_account_state_map(self):
        state_map = {}
        menu_set = self.terminalmenuset_set.prefetch_related("state_id", "account")
        for item in menu_set:
            state_map[str(item.account.pk)] = [state.pk for state in item.state_id.all()]
        return state_map

    @property
    def account_set_list(self) -> List[int]:
        return [item.account.get_hash() for item in self.terminalmenuset_set.all()]

    def get_hash(self) -> str:
        watch_list = ["powered", "blocked", "account_set_list"]
        return super()._hash_from_attrs(watch_list)

    def __str__(self):
        return f"Терминал <{self.mac_addr}> [ip: {self.ip}] {self.description}"

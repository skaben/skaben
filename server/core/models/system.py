from django.db import models

__all__ = ("System",)


class System(models.Model):
    ping_timeout = models.IntegerField(verbose_name="Задержка посыла PING в канал", default=10)

    keep_alive = models.IntegerField(
        verbose_name="Keep-alive", help_text="Интервал через который устройство будет считаться оффлайн", default=60
    )

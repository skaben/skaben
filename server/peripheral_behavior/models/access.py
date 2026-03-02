from django.db import models

__all__ = ["SkabenUser", "AccessCode", "Permission"]


MAX_USER_LENGTH = 96
MAX_CODE_LENGTH = 16


class SkabenUser(models.Model):
    """User model."""

    class Meta:
        verbose_name = "Игровой пользователь"
        verbose_name_plural = "Игровые пользователи"

    name = models.CharField(unique=True, verbose_name="Имя", max_length=MAX_USER_LENGTH)
    description = models.CharField(verbose_name="Описание", max_length=MAX_USER_LENGTH)

    def __str__(self):
        return f"User<{self.name}>"


class AccessCode(models.Model):
    """User access code."""

    class Meta:
        verbose_name = "Код доступа (ключ-карта)"
        verbose_name_plural = "Коды доступа (ключ-карты)"

    code = models.CharField(
        unique=True,
        verbose_name="Код доступа",
        help_text="Произвольный цифровой код или код карты",
        max_length=MAX_CODE_LENGTH,
    )
    user = models.ForeignKey(SkabenUser, on_delete=models.CASCADE)

    def __str__(self):
        return f"<{self.code}> {self.user.name}"


class Permission(models.Model):
    """Access codes permission to open locks."""

    class Meta:
        unique_together = ("card", "lock")
        verbose_name = "Доступ ключ-карты (права)"
        verbose_name_plural = "Доступы ключ-карт (права)"

    card = models.ForeignKey("peripheral_behavior.AccessCode", verbose_name="Ключ-карта", on_delete=models.CASCADE)
    lock = models.ForeignKey("peripheral_devices.LockDevice", verbose_name="Замок", on_delete=models.CASCADE)
    state_id = models.ManyToManyField("alert.AlertState", verbose_name="Уровень тревоги")

    def __str__(self):
        return f"Доступ {self.lock} - {self.card}"

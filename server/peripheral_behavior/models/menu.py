from dataclasses import dataclass
from core.models.base import BaseModelPolymorphic, BaseModelUUID, HashModelMixin
from core.helpers import get_hash_from
from django.db import models
import assets.models as asset_models
from peripheral_behavior.models import SkabenUser


@dataclass(frozen=True)
class MenuItemTypes:
    VIDEO_FILE: str = "video_file"
    AUDIO_FILE: str = "audio_file"
    IMAGE_FILE: str = "image_file"
    TEXT_FILE: str = "text_file"
    USER_INPUT: str = "user_input"

    CHOICES = {
        "text_file": "Текстовый файл",
        "user_input": "Пользовательский ввод",
        "video_file": "Видео",
        "audio_file": "Аудио",
        "image_file": "Изображение",
    }


MENU_ITEM_CHOICES = ((key, val) for key, val in MenuItemTypes.CHOICES.items())


class MenuItem(BaseModelPolymorphic, HashModelMixin):
    timer = models.SmallIntegerField(
        default=0, verbose_name="Время доступа", help_text="Ограничение на просмотр этого контента в секундах"
    )
    label = models.CharField(max_length=128, verbose_name="Надпись на кнопке")
    comment = models.CharField(
        max_length=128, blank=True, default="", verbose_name="Комментарий", help_text="Не будет виден игроку"
    )

    class Meta:
        verbose_name = "Пункт меню"
        verbose_name_plural = "Пункты меню"

    def get_hash(self) -> str:
        content_hash = ""
        if getattr(self, "content", None):
            content_hash = getattr(self.content, "hash", "")
        attrs_hash = super()._hash_from_attrs(
            [
                "timer",
                "label",
            ]
        )
        return get_hash_from([content_hash, attrs_hash])

    def __str__(self):
        return f"Пункт меню [{self.label}] {self.comment}"


class MenuItemAudio(MenuItem):
    content = models.ForeignKey(asset_models.AudioFile, on_delete=models.CASCADE, verbose_name="Связанное аудио")

    class Meta:
        verbose_name = "Аудио-документ"
        verbose_name_plural = "Аудио-документы"

    def __str__(self):
        return f"Меню: аудио [{self.label}]"


class MenuItemVideo(MenuItem):
    content = models.ForeignKey(asset_models.VideoFile, on_delete=models.CASCADE, verbose_name="Связанное видео")

    class Meta:
        verbose_name = "Видео-документ"
        verbose_name_plural = "Видео-документы"

    def __str__(self):
        return f"Меню: видео [{self.label}]"


class MenuItemImage(MenuItem):
    content = models.ForeignKey(asset_models.ImageFile, on_delete=models.CASCADE, verbose_name="Связанное изображение")

    class Meta:
        verbose_name = "Изображение"
        verbose_name_plural = "Изображения"

    def __str__(self):
        return f"Меню: изображение [{self.label}]"


class MenuItemText(MenuItem):
    content = models.ForeignKey(asset_models.TextFile, on_delete=models.CASCADE, verbose_name="Связанный текст")

    class Meta:
        verbose_name = "Текстовый документ"
        verbose_name_plural = "Текстовые документы"

    def __str__(self):
        return f"Меню: текст [{self.label}]"


class MenuItemUserInput(MenuItem):
    content = models.ForeignKey(asset_models.UserInput, on_delete=models.CASCADE, verbose_name="Пользовательский ввод")
    input_label = models.CharField(
        blank=True,
        default="",
        verbose_name="Заголовок поля ввода",
        help_text="Допустимая длина - 64 символа",
        max_length=64,
    )

    input_description = models.TextField(
        blank=True,
        default="",
        verbose_name="Текст на экране",
        help_text="Сообщение для пользователя на экране ввода (max 256 символов)",
        max_length=256,
    )

    class Meta:
        verbose_name = "Пользовательский ввод"
        verbose_name_plural = "Пользовательский ввод"

    def get_hash(self) -> str:
        content_hash = ""
        if getattr(self, "content", None):
            content_hash = getattr(self.content, "hash", "")
        attrs_hash = super()._hash_from_attrs(
            [
                "input_label",
                "input_description",
                "timer",
                "label",
            ]
        )
        return get_hash_from([content_hash, attrs_hash])

    def __str__(self):
        return f"Меню: ввод [{self.label}]"


class TerminalAccount(BaseModelUUID, HashModelMixin):
    """Terminal user account."""

    class Meta:
        verbose_name = "Пользовательское меню терминала"
        verbose_name_plural = "Пользовательские меню терминала"

    user = models.ForeignKey(SkabenUser, on_delete=models.CASCADE, verbose_name="Пользователь")
    password = models.CharField(
        null=True,
        blank=True,
        default="",
        verbose_name="Пароль",
        help_text="Для чтения пунктов меню потребуется известный пароль или успешный взлом терминала",
    )
    header = models.CharField(max_length=64, default="terminal vt40k")
    footer = models.CharField(max_length=64, default="unauthorized access is strictly prohibited")
    menu_items = models.ManyToManyField(MenuItem, related_name="menu_items")

    @property
    def has_files(self):
        files = {}
        for item in self.menu_items.all():
            related = getattr(item, item.option)
            if hasattr(related, "hash"):
                files.update({related.hash: related.uri})
        return files

    def get_hash(self) -> str:
        attrs_hash = super()._hash_from_attrs(["password", "header", "footer"])
        menu_items_hash = [item.get_hash() for item in self.menu_items.all()]
        return get_hash_from([attrs_hash, menu_items_hash])

    def __str__(self):
        protected = "PROTECTED" if self.password else "PUBLIC"
        return f"{self.user} <{protected}> terminal account"


class TerminalMenuSet(models.Model):
    """Набор доступных аккаунтов терминала."""

    account = models.ForeignKey("peripheral_behavior.TerminalAccount", verbose_name="Аккаунт", on_delete=models.CASCADE)
    terminal = models.ForeignKey("peripheral_devices.TerminalDevice", verbose_name="Терминал", on_delete=models.CASCADE)
    state_id = models.ManyToManyField("alert.AlertState", verbose_name="Уровень тревоги")

    def __str__(self):
        return "Аккаунт пользователя"

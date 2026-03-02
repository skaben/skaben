import time

from assets import storages
from core.helpers import get_hash_from, get_server_timestamp
from core.models.base import BaseModelUUID
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.utils.html import format_html
from assets.validators import alphanumeric_validator, audio_validator, video_validator, image_validator


class SkabenFile(BaseModelUUID):
    file: None

    class Meta:
        abstract = True

    name = models.CharField(max_length=128)
    hash = models.CharField(max_length=64, default="", editable=False)

    @property
    def uri(self):
        return f"{settings.BASE_URL}{self.file.path}"

    def save(self, *args, **kwargs):
        self.hash = get_hash_from(f"{get_server_timestamp()}{self.uuid}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self._meta.verbose_name} `{self.name}`"


class AudioFile(SkabenFile):
    class Meta:
        verbose_name = "Аудио файл"
        verbose_name_plural = "Аудио файлы"

    file = models.FileField(
        storage=storages.audio_storage,
        upload_to="audio/",
        help_text="поддерживаются .ogg, .wav, .mp3 файлы",
        validators=[audio_validator],
    )

    @property
    def audio_tag(self):
        return format_html(f'<audio controls src="{self.uri}"/>')

    audio_tag.fget.short_description = "Аудио"


class VideoFile(SkabenFile):
    class Meta:
        verbose_name = "Видео файл"
        verbose_name_plural = "Видео файлы"

    file = models.FileField(
        storage=storages.video_storage,
        upload_to="video/",
        help_text="поддерживаются .webm, .mp4 файлы",
        validators=[video_validator],
    )

    @property
    def video_tag(self):
        return format_html('<video controls width="320">' f'<source src="{self.uri}"/>' "</video>")

    video_tag.fget.short_description = "Видео"


class ImageFile(SkabenFile):
    class Meta:
        verbose_name = "Изображение"
        verbose_name_plural = "Изображения"

    file = models.ImageField(
        storage=storages.image_storage,
        upload_to="image/",
        help_text="поддерживаются .png, .jpg, .webp файлы",
        validators=[image_validator],
    )

    @property
    def image_tag(self):
        return format_html(f'<img src="{self.uri}" style="max-width: 400px; max-height: auto;"/>')

    image_tag.fget.short_description = "Изображение"


class TextFile(SkabenFile):
    class Meta:
        verbose_name = "Текстовый файл"
        verbose_name_plural = "Текстовые файлы"

    ident = models.CharField(
        max_length=128,
        unique=True,
        verbose_name="Идентификатор",
        help_text="Только латиница и цифры. Не будет виден игрокам.",
        validators=[alphanumeric_validator],
    )
    name = models.CharField(
        max_length=128, verbose_name="Название файла", help_text="Это название файла будет видно игрокам."
    )
    content = models.TextField(
        verbose_name="Содержимое", help_text="Введенный текст будет сконвертирован в текстовый файл после сохранения."
    )
    file = models.FileField(
        storage=storages.text_storage,
        upload_to="text/",
        null=True,
        blank=True,
    )

    @property
    def uri(self):
        return f"{settings.BASE_URL}{self.file.path}"

    uri.fget.short_description = "Ссылка на файл:"

    def save(self, *args, **kwargs):
        self.hash = get_hash_from(f"{round(time.time())}{self.uuid}")
        file = ContentFile(self.content)
        self.file.save(content=file, name=f"{self.uuid}_{self.ident}.txt", save=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self._meta.verbose_name} `{self.ident}` ({self.name})"

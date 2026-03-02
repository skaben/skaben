from core.admin import base_site
from django.contrib import admin
from .models.input import UserInput
from .models.files import VideoFile, AudioFile, ImageFile, TextFile


class FileAdmin(admin.ModelAdmin):
    exclude = ("hash",)
    readonly_fields = ("uri",)


class TextFileAdmin(admin.ModelAdmin):
    exclude = ("hash", "file")
    readonly_fields = ("uri",)


class ImageFileAdmin(FileAdmin):
    readonly_fields = ["uri", "image_tag"]


class AudioFileAdmin(FileAdmin):
    readonly_fields = ["uri", "audio_tag"]


base_site.register(AudioFile, AudioFileAdmin, site=base_site)
base_site.register(VideoFile, FileAdmin, site=base_site)
base_site.register(ImageFile, ImageFileAdmin, site=base_site)
base_site.register(TextFile, TextFileAdmin, site=base_site)
base_site.register(UserInput, admin.ModelAdmin, site=base_site)

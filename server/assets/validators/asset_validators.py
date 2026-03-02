from django.conf import settings
from django.core.validators import RegexValidator

from .file_validator import FileValidator

alphanumeric_validator = RegexValidator(regex=r"^[a-zA-Z0-9]+$", message="Only alphanumeric characters are allowed.")


def audio_validator(value):
    validator = FileValidator(
        max_size=settings.AUDIO_ASSET_MAX_SIZE * 1024 * 1024,
        allowed_extensions=["mp3", "wav", "ogg", "spx", "oga", "webm"],
        allowed_mimetypes=[
            "audio/webm",
            "audio/ogg",
            "audio/mpeg",
            "audio/vnd.wave",
            "audio/wav",
            "audio/wave",
            "audio/x-wav",
        ],
    )
    return validator(value)


def video_validator(value):
    validator = FileValidator(
        max_size=settings.VIDEO_ASSET_MAX_SIZE * 1024 * 1024,
        allowed_extensions=["webm", "mp4", "mp4v", "mpg4"],
        allowed_mimetypes=["video/webm", "video/mp4"],
    )
    return validator(value)


def image_validator(value):
    validator = FileValidator(
        max_size=settings.IMAGE_ASSET_MAX_SIZE * 1024 * 1024,
        allowed_extensions=["png", "jpg", "jpeg", "webp"],
        allowed_mimetypes=["image/png", "image/jpeg", "image/webp"],
    )
    return validator(value)

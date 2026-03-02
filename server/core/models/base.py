import re

from django.conf import settings
from polymorphic.models import PolymorphicModel
from core.helpers import get_uuid, get_server_timestamp, get_hash_from
from core.validators import mac_validator
from django.db import models


class HashModelMixin:
    def _hash_from_attrs(self, attrs: list[str]) -> str:
        return get_hash_from({attr: getattr(self, attr) for attr in attrs})

    def get_hash(self) -> str:
        raise NotImplementedError("Abstract method should be overridden by child model")


class BaseModelPolymorphic(PolymorphicModel):
    class Meta:
        abstract = True

    uuid = models.UUIDField(primary_key=True, default=get_uuid, editable=False)


class BaseModelUUID(models.Model):
    """Model with UUID PK."""

    class Meta:
        abstract = True

    uuid = models.UUIDField(primary_key=True, default=get_uuid, editable=False)


class DeviceKeepalive(models.Model):
    """Device keepalive record keeper"""

    mac_addr = models.CharField(max_length=32, validators=[mac_validator])
    timestamp = models.PositiveIntegerField()

    @property
    def online(self):
        return self.timestamp + settings.DEVICE_KEEPALIVE_TIMEOUT > get_server_timestamp()

    def save(self, *args, **kwargs):
        self.mac_addr = re.sub(r"[^a-zA-Z0-9]", "", self.mac_addr)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Keepalive: {self.mac_addr} {self.online}"

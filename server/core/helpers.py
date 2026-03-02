from typing import Optional

import base64
import hashlib
import json
import re
import time
import uuid as _uuid
from datetime import datetime
from random import sample
from string import ascii_lowercase

import pytz
from django.conf import settings


def get_server_timestamp() -> int:
    return int(time.time())


def get_uuid():
    return _uuid.uuid4()


def from_json(json_data: str | dict = dict) -> dict:
    """Получение данных из json"""
    if isinstance(json_data, dict):
        return json_data
    return json.loads(json_data)


def get_task_id() -> str:
    """Генерирует task id"""
    random_string = "".join(sample(ascii_lowercase, 5)) + str(get_server_timestamp())
    hasher = hashlib.md5(bytes(random_string, encoding="utf-8"))
    return base64.urlsafe_b64encode(hasher.digest()).decode("utf-8")


def get_hash_from(data: list | dict | str, encoding: Optional[str] = "utf-8") -> str:
    """Simple hashing function"""
    if isinstance(data, dict) or isinstance(data, list):
        dump = json.dumps(data).encode(encoding)
    elif isinstance(data, str):
        dump = bytes(data, encoding=encoding)
    else:
        raise TypeError(f"{type(data)} not supported, provide `dict`, `list` or `str` instead")
    return hashlib.md5(dump).hexdigest()


def timestamp_expired(timestamp: int) -> bool:
    """Check if timestamp is older than keepalive timeout"""
    keep_alive = int(time.time()) - 60  # todo: get from system settings
    return timestamp <= keep_alive


def get_time(timestamp: int) -> str:
    """Convert unix timestamp to local time."""
    utc_time = datetime.utcfromtimestamp(timestamp)
    local = (
        pytz.utc.localize(utc_time, is_dst=None)
        .astimezone(pytz.timezone(settings.TIME_ZONE))
        .strftime("%Y-%m-%d %H:%M:%S")
    )
    return local


def hex_to_rgb(hexdata: str) -> str:
    """Convert hex to hsl."""
    if hexdata.startswith("#"):
        hexdata = hexdata[1:]
    hexdata = "".join([h.lower() for h in hexdata])
    return ",".join([str(i) for i in bytes.fromhex(hexdata)])


def format_mac_address(mac_address: str) -> str:
    """Converts MAC to standart format."""
    cleaned_mac = re.sub(r"[^a-zA-Z0-9]", "", mac_address)
    return ":".join(cleaned_mac[i : i + 2] for i in range(0, len(cleaned_mac), 2))


def format_routing_key(*args) -> str:
    """Formats routing key for Rabbit."""
    return ".".join([arg for arg in args])

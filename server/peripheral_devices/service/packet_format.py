import logging
from typing import Optional
from pydantic import ValidationError

from core.helpers import get_server_timestamp
from core.transport.packets import CUP


def cup_packet_from_smart(model) -> Optional[CUP]:
    """Формирует пакет с данными для апдейта клиента."""
    try:
        packet = CUP(
            topic=model.topic,
            uid=model.mac_addr,
            config_hash=model.get_hash(),
            timestamp=get_server_timestamp(),
            datahold=model.to_mqtt_config(),
        )
        return packet
    except ValidationError:  # noqa
        logging.exception("cannot form cup packet")
        return


def cup_packet_from_simple(topic: str, payload: dict, mac_addr: Optional[str] = None) -> Optional[CUP]:
    device_uid = mac_addr or "all"
    try:
        packet = CUP(
            topic=topic,
            uid=device_uid,
            timestamp=get_server_timestamp(),
            datahold=payload,
        )
        return packet
    except ValidationError:  # noqa
        logging.exception("cannot form cup packet")
        return

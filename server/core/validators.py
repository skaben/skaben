import netaddr
from django.core.exceptions import ValidationError


def mac_validator(mac_addr: str):
    try:
        if len(mac_addr) < 12:
            raise ValidationError("MAC address is too short")
        mac_addr = str(netaddr.EUI(mac_addr, dialect=netaddr.mac_bare)).lower()
    except (netaddr.AddrFormatError, ValueError):
        raise ValidationError(f"Invalid MAC address format: {mac_addr}")

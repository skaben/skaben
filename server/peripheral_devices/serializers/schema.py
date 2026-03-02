from typing import Dict, List, Optional
from pydantic import BaseModel


class BaseDeviceSchema(BaseModel):
    alert: str
    override: bool


class LockDeviceSendSchema(BaseDeviceSchema):
    sound: bool
    closed: bool
    blocked: bool
    timer: int
    acl: Dict[str, List[int]]


class LockDeviceSaveSchema(BaseModel):
    closed: Optional[bool]
    blocked: Optional[bool] = None


class TerminalDeviceSchema(BaseDeviceSchema):
    powered: bool
    blocked: bool

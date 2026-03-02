from dataclasses import dataclass


@dataclass(frozen=True)
class SkabenTaskType:
    PINGER: str = "pinger_task"
    ALERT: str = "alert_changer_task"
    UPDATE_DEVICE: str = "update_device_task"

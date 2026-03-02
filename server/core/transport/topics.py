from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class SkabenTopics:
    RGB = "rgb"
    SCL = "scl"
    PWR = "pwr"
    BOX = "box"
    LOCK = "lock"
    TERMINAL = "terminal"

    @property
    def smart(self) -> List[str]:
        return [self.LOCK, self.TERMINAL]

    @property
    def simple(self) -> List[str]:
        return [self.BOX, self.RGB, self.SCL, self.PWR]

    @property
    def all(self) -> List[str]:
        return self.simple + self.smart


def get_topics():
    return SkabenTopics()

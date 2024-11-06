from typing import Any


class TrailingStopConfig:
    def __init__(self, threshold, sl_adjustment, tp_adjustment) -> None:
        self.threshold = threshold
        self.sl_adjustment = sl_adjustment
        self.tp_adjustment = tp_adjustment

from __future__ import annotations

from collections import Counter
from typing import Dict


class Metrics:
    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()

    def inc(self, key: str, value: int = 1) -> None:
        self._counters[key] += value

    def get(self, key: str, default: int = 0) -> int:
        return self._counters.get(key, default)

    def dump(self) -> Dict[str, int]:
        return dict(self._counters)

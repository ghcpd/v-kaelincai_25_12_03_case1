from __future__ import annotations

import time
from typing import Dict
from domain.models import GraphData


class MockGraphAPI:
    def __init__(self, mode: str = "immediate", delay_seconds: float = 0.0, failures_before_success: int = 0):
        self.mode = mode
        self.delay_seconds = delay_seconds
        self.failures_before_success = failures_before_success
        self._failures = 0

    def fetch_graph(self, graph_id: str) -> GraphData:
        if self.mode == "delayed":
            time.sleep(self.delay_seconds)
        if self.mode == "pending":
            # Simulate transient failure
            if self._failures < self.failures_before_success:
                self._failures += 1
                raise RuntimeError("graph not ready")
        return GraphData(edges=[
            # default graph same as legacy
            {"source": "A", "target": "B", "weight": 5},
            {"source": "A", "target": "C", "weight": 2},
            {"source": "C", "target": "D", "weight": 1},
            {"source": "D", "target": "F", "weight": -3},
            {"source": "F", "target": "B", "weight": 1},
            {"source": "A", "target": "E", "weight": 1},
            {"source": "E", "target": "B", "weight": 6},
        ])

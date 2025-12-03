from __future__ import annotations

from typing import List, Tuple
from domain.models import PlanStatus


class StateMachine:
    def __init__(self) -> None:
        self.state = PlanStatus.INIT
        self.history: List[Tuple[PlanStatus, str]] = []

    def transition(self, new_state: PlanStatus, reason: str = "") -> None:
        self.history.append((self.state, reason))
        self.state = new_state

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "history": [(str(s), r) for s, r in self.history],
        }

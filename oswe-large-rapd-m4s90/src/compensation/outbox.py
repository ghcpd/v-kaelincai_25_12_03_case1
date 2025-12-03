from __future__ import annotations

from typing import List, Optional
from domain.models import OutboxEvent, PlanStatus


class TransactionalOutbox:
    def __init__(self) -> None:
        self._events: List[OutboxEvent] = []

    def append(self, request_id: str, status: PlanStatus, path=None, cost=None, error: Optional[str] = None) -> None:
        self._events.append(OutboxEvent(request_id=request_id, status=status, path=path, cost=cost, error=error))

    def all(self) -> List[OutboxEvent]:
        return list(self._events)

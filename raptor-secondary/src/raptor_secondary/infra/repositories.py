from __future__ import annotations

from threading import Lock
from typing import Dict, Optional, List
from datetime import datetime, timezone
from uuid import uuid4

from raptor_secondary.domain.models import Appointment, AppointmentRequest, OutboxEvent, AppointmentState


class InMemoryAppointmentRepository:
    def __init__(self) -> None:
        self._store: Dict[str, Appointment] = {}
        self._lock = Lock()

    def get(self, request_id: str) -> Optional[Appointment]:
        with self._lock:
            return self._store.get(request_id)

    def save(self, request: AppointmentRequest) -> Appointment:
        now = datetime.now(timezone.utc)
        appt = Appointment(
            request_id=request.request_id,
            state=AppointmentState.INIT,
            provider_id=request.provider_id,
            customer_id=request.customer_id,
            appointment_time=request.appointment_time,
            duration_minutes=request.duration_minutes,
            location=request.location,
            priority=request.priority,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._store[request.request_id] = appt
        return appt

    def update(self, appt: Appointment) -> Appointment:
        appt.updated_at = datetime.now(timezone.utc)
        with self._lock:
            self._store[appt.request_id] = appt
        return appt

    def all(self) -> List[Appointment]:
        with self._lock:
            return list(self._store.values())


class InMemoryOutboxRepository:
    def __init__(self) -> None:
        self._events: Dict[str, OutboxEvent] = {}
        self._lock = Lock()

    def enqueue(self, request_id: str, type: str, payload: dict) -> OutboxEvent:
        event_id = str(uuid4())
        evt = OutboxEvent(
            event_id=event_id,
            request_id=request_id,
            type=type,
            payload=payload,
            available_at=datetime.now(timezone.utc),
            sent_at=None,
        )
        with self._lock:
            self._events[event_id] = evt
        return evt

    def mark_sent(self, event_id: str) -> None:
        with self._lock:
            evt = self._events.get(event_id)
            if evt:
                evt.sent_at = datetime.now(timezone.utc)
                self._events[event_id] = evt

    def list_pending(self) -> List[OutboxEvent]:
        with self._lock:
            return [e for e in self._events.values() if e.sent_at is None]

    def all(self) -> List[OutboxEvent]:
        with self._lock:
            return list(self._events.values())

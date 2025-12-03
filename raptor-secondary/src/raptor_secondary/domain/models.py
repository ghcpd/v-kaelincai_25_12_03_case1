from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, Field


class AppointmentPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class AppointmentState(str, Enum):
    INIT = "INIT"
    IN_PROGRESS = "IN_PROGRESS"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"


StrippedStr = Annotated[str, Field(min_length=1)]


class AppointmentRequest(BaseModel):
    request_id: StrippedStr = Field(..., description="Idempotency key")
    customer_id: StrippedStr
    appointment_time: datetime
    duration_minutes: int = Field(..., gt=0)
    location: StrippedStr
    provider_id: StrippedStr
    priority: AppointmentPriority = AppointmentPriority.NORMAL

    model_config = {
        "str_strip_whitespace": True,
        "extra": "allow",
    }


class Appointment(BaseModel):
    request_id: str
    state: AppointmentState = AppointmentState.INIT
    provider_id: str
    customer_id: str
    appointment_time: datetime
    duration_minutes: int
    location: str
    priority: AppointmentPriority
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    last_error: Optional[str] = None

    model_config = {
        "str_strip_whitespace": True
    }


class OutboxEvent(BaseModel):
    event_id: str
    request_id: str
    type: str
    payload: dict
    available_at: datetime
    sent_at: Optional[datetime] = None

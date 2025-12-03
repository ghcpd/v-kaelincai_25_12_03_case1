from __future__ import annotations

from typing import Tuple
from raptor_secondary.domain.models import AppointmentState


ALLOWED_TRANSITIONS = {
    AppointmentState.INIT: {AppointmentState.IN_PROGRESS},
    AppointmentState.IN_PROGRESS: {AppointmentState.CONFIRMED, AppointmentState.FAILED, AppointmentState.COMPENSATING},
    AppointmentState.CONFIRMED: {AppointmentState.COMPENSATING},
    AppointmentState.COMPENSATING: {AppointmentState.COMPENSATED, AppointmentState.FAILED},
    AppointmentState.FAILED: {AppointmentState.IN_PROGRESS},
    AppointmentState.COMPENSATED: set(),
}


def can_transition(current: AppointmentState, target: AppointmentState) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def transition(current: AppointmentState, target: AppointmentState) -> Tuple[bool, str]:
    if can_transition(current, target):
        return True, ""
    return False, f"Invalid transition {current} -> {target}"

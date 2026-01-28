from __future__ import annotations

import time
from typing import Optional
from dataclasses import dataclass

from raptor_secondary.domain.models import AppointmentRequest, AppointmentState
from raptor_secondary.infra.config import AppConfig
from raptor_secondary.infra.repositories import InMemoryAppointmentRepository, InMemoryOutboxRepository
from raptor_secondary.services.state_machine import transition
from raptor_secondary.adapters.external_provider import ExternalProviderClient, ProviderError, ProviderTimeout
from raptor_secondary.infra.circuit_breaker import CircuitBreaker
from raptor_secondary.infra.logging import get_logger, mask_value


@dataclass
class ExecutionResult:
    request_id: str
    state: AppointmentState
    retries: int
    idempotent_hit: bool
    last_error: Optional[str]


class AppointmentService:
    def __init__(self, *, provider_client: ExternalProviderClient, appointments: InMemoryAppointmentRepository, outbox: InMemoryOutboxRepository, config: AppConfig) -> None:
        self.provider_client = provider_client
        self.appointments = appointments
        self.outbox = outbox
        self.config = config
        self.breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker.failure_threshold,
            reset_timeout_seconds=config.circuit_breaker.reset_timeout_seconds,
        )
        self.logger = get_logger(service="appointment_service")

    def process(self, req: AppointmentRequest) -> ExecutionResult:
        logger = self.logger.bind(request_id=mask_value(req.request_id))
        existing = self.appointments.get(req.request_id)
        if existing:
            logger.info("idempotent_hit", state=str(existing.state))
            return ExecutionResult(
                request_id=req.request_id,
                state=existing.state,
                retries=existing.retry_count,
                idempotent_hit=True,
                last_error=existing.last_error,
            )

        appt = self.appointments.save(req)
        ok, reason = transition(appt.state, AppointmentState.IN_PROGRESS)
        if not ok:
            logger.error("invalid_transition", reason=reason)
            appt.last_error = reason
            self.appointments.update(appt)
            return ExecutionResult(req.request_id, appt.state, appt.retry_count, False, appt.last_error)
        appt.state = AppointmentState.IN_PROGRESS
        self.appointments.update(appt)
        logger.info("started")

        # Circuit breaker
        if not self.breaker.allow_request():
            logger.warning("circuit_open")
            appt.state = AppointmentState.FAILED
            appt.last_error = "circuit_open"
            self.appointments.update(appt)
            return ExecutionResult(req.request_id, appt.state, appt.retry_count, False, appt.last_error)

        attempt = 0
        while attempt < self.config.retry.max_attempts:
            try:
                attempt += 1
                appt.retry_count = attempt - 1
                self.appointments.update(appt)
                status, data = self.provider_client.schedule(
                    {"request_id": req.request_id, "mode": getattr(req, "mode", "immediate")},
                    timeout=self.config.timeout.schedule_timeout_seconds,
                )
                self.breaker.on_success()

                if status == "CONFIRMED":
                    appt.state = AppointmentState.CONFIRMED
                    appt.last_error = None
                    self.appointments.update(appt)
                    # Outbox event
                    evt = self.outbox.enqueue(req.request_id, "AppointmentConfirmed", {"confirmation": data})
                    logger.info("confirmed", event_id=evt.event_id)
                    # Simulate dispatch for test (mark sent)
                    self.outbox.mark_sent(evt.event_id)
                    # If downstream fail hint, trigger compensation
                    if data.get("downstream_fail"):
                        self._compensate(appt, reason="downstream_fail")
                    return ExecutionResult(req.request_id, appt.state, appt.retry_count, False, appt.last_error)
                elif status == "PENDING":
                    # For simplicity, immediately treat as success for demo
                    appt.state = AppointmentState.CONFIRMED
                    self.appointments.update(appt)
                    evt = self.outbox.enqueue(req.request_id, "AppointmentConfirmed", {"confirmation": data})
                    self.outbox.mark_sent(evt.event_id)
                    logger.info("confirmed_from_pending", event_id=evt.event_id)
                    return ExecutionResult(req.request_id, appt.state, appt.retry_count, False, appt.last_error)
                else:
                    raise ProviderError(f"unexpected status {status}")
            except ProviderTimeout as e:
                self.breaker.on_failure()
                appt.last_error = "timeout"
                self.appointments.update(appt)
                logger.warning("schedule_timeout", attempt=attempt)
            except ProviderError as e:
                self.breaker.on_failure()
                appt.last_error = str(e)
                self.appointments.update(appt)
                logger.warning("schedule_error", attempt=attempt, error=str(e))

            # backoff
            if attempt < self.config.retry.max_attempts:
                sleep_for = min(
                    self.config.retry.backoff_initial_seconds * (self.config.retry.backoff_factor ** (attempt - 1)),
                    self.config.retry.backoff_max_seconds,
                )
                time.sleep(sleep_for)

        # Exhausted retries
        appt.state = AppointmentState.FAILED
        self.appointments.update(appt)
        logger.error("failed_exhausted", attempts=attempt)
        return ExecutionResult(req.request_id, appt.state, appt.retry_count, False, appt.last_error)

    def _compensate(self, appt, reason: str):
        logger = self.logger.bind(request_id=appt.request_id)
        ok, reason_txt = transition(appt.state, AppointmentState.COMPENSATING)
        if not ok:
            logger.error("compensation_invalid_transition", reason=reason_txt)
            return
        appt.state = AppointmentState.COMPENSATING
        self.appointments.update(appt)
        try:
            status, data = self.provider_client.cancel({"request_id": appt.request_id}, timeout=self.config.timeout.cancel_timeout_seconds)
            if status == "CANCELLED":
                appt.state = AppointmentState.COMPENSATED
                appt.last_error = None
                self.appointments.update(appt)
                evt = self.outbox.enqueue(appt.request_id, "AppointmentCompensated", {"cancel": data, "reason": reason})
                self.outbox.mark_sent(evt.event_id)
                logger.info("compensated", event_id=evt.event_id)
            else:
                appt.state = AppointmentState.FAILED
                appt.last_error = f"compensation_failed: {status}"
                self.appointments.update(appt)
        except ProviderTimeout:
            appt.state = AppointmentState.FAILED
            appt.last_error = "compensation_timeout"
            self.appointments.update(appt)
            logger.warning("compensation_timeout")
        except ProviderError as e:
            appt.state = AppointmentState.FAILED
            appt.last_error = str(e)
            self.appointments.update(appt)
            logger.warning("compensation_error", error=str(e))

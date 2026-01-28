import json
import os
import time
import pytest

from pathlib import Path
from typing import List

from raptor_secondary.domain.models import AppointmentRequest, AppointmentState
from raptor_secondary.services.appointment_service import ExecutionResult

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "test_data.json"
EXPECTED_PATH = Path(__file__).resolve().parents[1] / "data" / "expected_postchange.json"
LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "log_post.txt"


def load_test_case(case_id: str) -> dict:
    data = json.loads(DATA_PATH.read_text())
    for c in data:
        if c["id"] == case_id:
            return c
    raise KeyError(case_id)


@pytest.mark.parametrize("case_id", ["happy-path-01"])
def test_happy_path(service, repositories, case_id):
    case = load_test_case(case_id)
    req = AppointmentRequest(**{k: v for k, v in case.items() if k not in {"id", "mode"}})
    # attach mode dynamically
    req.mode = case.get("mode", "immediate")
    res: ExecutionResult = service.process(req)
    assert res.state == AppointmentState.CONFIRMED
    assert res.retries == 0
    assert not res.idempotent_hit
    # Outbox should have one confirmed event
    outbox = repositories["outbox"].all()
    assert any(evt.type == "AppointmentConfirmed" and evt.request_id == req.request_id for evt in outbox)


def test_idempotency(service, repositories):
    case = load_test_case("idempotent-retry")
    req = AppointmentRequest(**{k: v for k, v in case.items() if k not in {"id", "mode"}})
    req.mode = case.get("mode", "immediate")
    res1 = service.process(req)
    res2 = service.process(req)
    assert res1.state == AppointmentState.CONFIRMED
    assert res2.state == AppointmentState.CONFIRMED
    assert res2.idempotent_hit is True
    # Outbox should still have only one event for this request
    outbox_events = [e for e in repositories["outbox"].all() if e.request_id == req.request_id]
    assert len(outbox_events) == 1


def test_flaky_retry(service, repositories):
    case = load_test_case("flaky-retry-success")
    req = AppointmentRequest(**{k: v for k, v in case.items() if k not in {"id", "mode"}})
    req.mode = case.get("mode", "flaky")
    res = service.process(req)
    assert res.state == AppointmentState.CONFIRMED
    assert res.retries >= 1


def test_timeout_circuit_breaker(service, repositories):
    case = load_test_case("timeout-simulated")
    req1 = AppointmentRequest(**{k: v for k, v in case.items() if k not in {"id", "mode"}})
    req1.mode = case.get("mode", "timeout")
    res = service.process(req1)
    assert res.state == AppointmentState.FAILED
    assert res.last_error == "timeout"

    # Circuit breaker should open after configured failures (2). Trigger another request to confirm fast-fail without idempotency.
    req2 = AppointmentRequest(**{k: v for k, v in case.items() if k not in {"id", "mode"}})
    req2.request_id = req1.request_id + "-bis"
    req2.mode = case.get("mode", "timeout")
    res2 = service.process(req2)
    assert res2.state == AppointmentState.FAILED
    assert res2.last_error in ("circuit_open", "timeout")


def test_compensation(service, repositories):
    case = load_test_case("compensation-needed")
    req = AppointmentRequest(**{k: v for k, v in case.items() if k not in {"id", "mode"}})
    req.mode = case.get("mode", "confirm_fail")
    res = service.process(req)
    assert res.state == AppointmentState.COMPENSATED
    outbox_types = [e.type for e in repositories["outbox"].all() if e.request_id == req.request_id]
    assert "AppointmentConfirmed" in outbox_types
    assert "AppointmentCompensated" in outbox_types


def test_audit_logs_present(service, repositories):
    # Ensure log file has entries for past requests
    if LOG_FILE.exists():
        lines = LOG_FILE.read_text().strip().splitlines()
    else:
        lines = []
    assert len(lines) > 0
    # Check that at least one line contains masked ids
    import json as _json
    found_masked = False
    for line in lines:
        try:
            obj = _json.loads(line)
        except Exception:
            continue
        if "request_id" in obj:
            rid = obj["request_id"]
            if "***" in rid:
                found_masked = True
                break
    assert found_masked

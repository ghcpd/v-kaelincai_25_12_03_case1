from __future__ import annotations

import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

# In-memory counters by request_id for behaviors like flaky
_call_counts: Dict[str, int] = {}


class ScheduleRequest(BaseModel):
    request_id: str
    mode: str = "immediate"


class CancelRequest(BaseModel):
    request_id: str


@app.post("/api/v2/schedule")
def schedule(req: ScheduleRequest):
    count = _call_counts.get(req.request_id, 0) + 1
    _call_counts[req.request_id] = count
    mode = req.mode

    if mode == "immediate":
        return {"status": "CONFIRMED", "confirmation_id": f"conf-{req.request_id}"}
    if mode == "pending":
        return {"status": "PENDING", "confirmation_id": f"conf-{req.request_id}"}
    if mode == "flaky":
        if count == 1:
            raise HTTPException(status_code=500, detail="transient error")
        return {"status": "CONFIRMED", "confirmation_id": f"conf-{req.request_id}"}
    if mode == "timeout":
        time.sleep(2)  # exceed typical timeout
        return {"status": "CONFIRMED", "confirmation_id": f"conf-{req.request_id}"}
    if mode == "compensation_needed":
        # Simulate partial success requiring compensation later
        return {"status": "CONFIRMED", "confirmation_id": f"conf-{req.request_id}", "compensation_hint": True}
    if mode == "confirm_fail":
        # Simulate success but outbox/other failure triggers compensation
        return {"status": "CONFIRMED", "confirmation_id": f"conf-{req.request_id}", "downstream_fail": True}

    raise HTTPException(status_code=400, detail=f"unknown mode {mode}")


@app.post("/api/v2/cancel")
def cancel(req: CancelRequest):
    # Always succeed for simplicity
    return {"status": "CANCELLED", "request_id": req.request_id}


@app.post("/internal/reset")
def reset():
    _call_counts.clear()
    return {"ok": True}

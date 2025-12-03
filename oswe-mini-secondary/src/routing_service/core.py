from __future__ import annotations

from enum import Enum
from typing import Dict, Any, Optional
import uuid
import time

from .graph import Graph
from . import algorithms


class RoutingError(Exception):
    pass


class RouterState(Enum):
    INIT = "init"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Router:
    """Higher-level router: chooses algorithm, supports idempotency, outbox and lifecycle.

    This is intended as a greenfield runtime shim for appointment-like requests that
    must be idempotent, retry-friendly and observable.
    """

    def __init__(self, graph: Graph, logger=None):
        self.graph = graph
        self.logger = logger or (lambda **kwargs: print(kwargs))

        # In-memory stores for demo/testing
        self.appointments: Dict[str, Dict[str, Any]] = {}
        self.outbox: Dict[str, Dict[str, Any]] = {}

    def _log(self, request_id: str, message: str, **extra):
        entry = {"request_id": request_id, "message": message, **extra}
        self.logger(**entry)

    def create_request_id(self) -> str:
        return str(uuid.uuid4())

    def route(self, start: str, goal: str, request_id: Optional[str] = None, idempotency_key: Optional[str] = None, algorithm: str = "auto", timeout_seconds: float = 5.0):
        request_id = request_id or self.create_request_id()
        idempotency_key = idempotency_key or request_id

        # Idempotency: if appointment exists and has SUCCEEDED, return cached outcome.
        # If previous attempt FAILED we allow retries (transient vs permanent failures
        # can be handled via richer failure categorization; this prototype allows
        # a retry after failure).
        if idempotency_key in self.appointments:
            item = self.appointments[idempotency_key]
            if item["state"] == RouterState.SUCCEEDED:
                self._log(request_id, "idempotent-return", state=item["state"].value)
                return item["result"]
            # If FAILED, we're allowing a retry — reset state to INIT for a fresh attempt
            if item["state"] == RouterState.FAILED:
                self._log(request_id, "retry-after-failed", state=item["state"].value)
                self.appointments[idempotency_key] = {"state": RouterState.INIT, "created_at": time.time(), "result": None}

        self.appointments[idempotency_key] = {"state": RouterState.INIT, "created_at": time.time(), "result": None}

        self._log(request_id, "start", start=start, goal=goal)
        self.appointments[idempotency_key]["state"] = RouterState.IN_PROGRESS

        # Choose algorithm
        if algorithm == "auto":
            algorithm = "bellman-ford" if self.graph.has_negative_weight() else "dijkstra"

        # Attempt routing with timeout
        start_ts = time.time()
        try:
            if algorithm == "dijkstra":
                path, cost = algorithms.dijkstra_shortest_path(self.graph, start, goal)
            elif algorithm == "bellman-ford":
                path, cost = algorithms.bellman_ford_shortest_path(self.graph, start, goal)
            else:
                raise RoutingError(f"unknown algorithm {algorithm}")

            elapsed = time.time() - start_ts
            if elapsed > timeout_seconds:
                raise TimeoutError("routing timed out")

            result = {"path": path, "cost": cost, "algorithm": algorithm}
            self.appointments[idempotency_key]["state"] = RouterState.SUCCEEDED
            self.appointments[idempotency_key]["result"] = result

            # Outbox: persist event for downstream (simulate)
            outbox_id = str(uuid.uuid4())
            self.outbox[outbox_id] = {"request_id": request_id, "event": "routing.succeeded", "payload": result}
            self._log(request_id, "succeeded", result=result, outbox_id=outbox_id)
            return result

        except algorithms.ValidationError as ve:
            # Immediate validation error (e.g., negative weights invalid for Dijkstra)
            self.appointments[idempotency_key]["state"] = RouterState.FAILED
            self.appointments[idempotency_key]["result"] = {"error": str(ve)}
            self._log(request_id, "validation-error", error=str(ve))
            raise

        except Exception as exc:
            # Generic failure -> set FAILED and put compensating event in outbox
            self.appointments[idempotency_key]["state"] = RouterState.FAILED
            self.appointments[idempotency_key]["result"] = {"error": str(exc)}
            outbox_id = str(uuid.uuid4())
            self.outbox[outbox_id] = {"request_id": request_id, "event": "routing.failed", "payload": {"error": str(exc)}}
            self._log(request_id, "failed", error=str(exc), outbox_id=outbox_id)
            raise

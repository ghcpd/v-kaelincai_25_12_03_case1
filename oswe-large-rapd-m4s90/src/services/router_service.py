from __future__ import annotations

from typing import Callable, Dict
from domain.models import RouteRequest, RouteResponse, PlanStatus, GraphData
from services.state_machine import StateMachine
from services.retry import with_retry
from algorithms import dijkstra, bellman_ford
from instrumentation.logging import get_logger
from instrumentation.metrics import Metrics
from compensation.outbox import TransactionalOutbox

logger = get_logger(__name__)


class RouterService:
    def __init__(self, metrics: Metrics | None = None, outbox: TransactionalOutbox | None = None):
        self._cache: Dict[str, RouteResponse] = {}
        self.metrics = metrics or Metrics()
        self.outbox = outbox or TransactionalOutbox()

    def route(self, request: RouteRequest, graph_loader: Callable[[], GraphData]) -> RouteResponse:
        if request.request_id in self._cache:
            resp = self._cache[request.request_id]
            self.metrics.inc('idempotent_hits')
            logger.info({"event": "cache_hit", "request_id": request.request_id})
            return resp

        sm = StateMachine()
        sm.transition(PlanStatus.VALIDATED, "request received")

        attempts = 0
        try:
            sm.transition(PlanStatus.FETCH_GRAPH, "loading graph")

            def _load() -> GraphData:
                nonlocal attempts
                attempts += 1
                self.metrics.inc('graph_load_attempts')
                return graph_loader()

            graph: GraphData = with_retry(_load, retries=2, backoff=0.1, timeout=request.timeout_seconds)
            sm.transition(PlanStatus.PLANNING, "selecting algorithm")

            adj = graph.adjacency()
            if graph.has_negative_edge():
                algo_name = 'bellman_ford'
                path, cost = bellman_ford.shortest_path(adj, request.source, request.target)
            else:
                algo_name = 'dijkstra'
                path, cost = dijkstra.shortest_path(adj, request.source, request.target)
            sm.transition(PlanStatus.SUCCESS, "route planned")
            resp = RouteResponse(
                request_id=request.request_id,
                path=path,
                cost=cost,
                algorithm=algo_name,
                status=PlanStatus.SUCCESS,
                retries=max(attempts - 1, 0),
            )
            self._cache[request.request_id] = resp
            self.metrics.inc('success')
            self.outbox.append(request.request_id, PlanStatus.SUCCESS, path=path, cost=cost)
            logger.info({"event": "route_success", "request_id": request.request_id, "algorithm": algo_name, "path": path, "cost": cost, "state": sm.snapshot()})
            return resp
        except Exception as exc:  # noqa: BLE001
            sm.transition(PlanStatus.FAILURE, str(exc))
            self.metrics.inc('failure')
            self.outbox.append(request.request_id, PlanStatus.FAILURE, error=str(exc))
            logger.error({"event": "route_failure", "request_id": request.request_id, "error": str(exc), "state": sm.snapshot()})
            return RouteResponse(
                request_id=request.request_id,
                status=PlanStatus.FAILURE,
                error=str(exc),
                retries=max(attempts - 1, 0),
            )

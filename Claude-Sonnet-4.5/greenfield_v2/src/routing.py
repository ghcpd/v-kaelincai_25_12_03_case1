"""Routing service orchestration layer with resilience patterns."""
import time
import uuid
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .core.graph import Graph, GraphValidationError
from .core.algorithms import AlgorithmSelector, NegativeCycleError
from .core.validator import ResultValidator, ValidationError
from .resilience import (
    retry,
    TransientError,
    timeout,
    TimeoutError,
    CircuitBreaker,
    CircuitBreakerOpenError,
    IdempotencyCache,
)
from .observability import get_logger, metrics


logger = get_logger(__name__)


@dataclass
class RouteRequest:
    """Route request with idempotency support."""
    request_id: str
    graph_id: str
    start_node: str
    goal_node: str
    algorithm_hint: str = "auto"
    timeout_ms: int = 5000
    validate_result: bool = True


@dataclass
class RouteResponse:
    """Route response with metadata."""
    request_id: str
    status: str  # "success", "error", "timeout"
    path: Optional[List[str]] = None
    cost: Optional[float] = None
    metadata: Optional[dict] = None
    error: Optional[dict] = None


class RoutingEngine:
    """
    Routing engine with resilience patterns.
    
    Features:
    - Idempotency via request ID cache
    - Retry with exponential backoff for transient failures
    - Timeout enforcement
    - Circuit breaker for cascading failure prevention
    - Automatic algorithm selection
    - Result validation
    - Structured logging and metrics
    """
    
    def __init__(self, graph_loader_func=None):
        """
        Initialize routing engine.
        
        Args:
            graph_loader_func: Optional custom graph loader (for testing)
        """
        self.cache = IdempotencyCache(maxsize=1000, default_ttl=300.0)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout_duration=60.0,
            expected_exceptions=(GraphValidationError, IOError)
        )
        self._graph_loader = graph_loader_func or self._default_graph_loader
    
    def compute_route(self, request: RouteRequest) -> RouteResponse:
        """
        Compute route with resilience patterns.
        
        Flow:
        1. Check idempotency cache
        2. Load graph (with retry + circuit breaker)
        3. Select algorithm
        4. Compute path (with timeout)
        5. Validate result
        6. Cache result
        7. Return response
        """
        start_time = time.time()
        
        try:
            # Log request
            logger.info(
                "Route request received",
                extra={
                    "request_id": request.request_id,
                    "graph_id": request.graph_id,
                    "start_node": request.start_node,
                    "goal_node": request.goal_node,
                }
            )
            
            # Check cache (idempotency)
            cached_result = self.cache.get(
                request.request_id,
                graph_id=request.graph_id,
                start_node=request.start_node,
                goal_node=request.goal_node,
            )
            
            if cached_result is not None:
                logger.info(
                    "Cache hit",
                    extra={"request_id": request.request_id, "graph_id": request.graph_id}
                )
                metrics.cache_hit_total.labels(graph_id=request.graph_id).inc()
                cached_result.metadata["cache_hit"] = True
                return cached_result
            
            metrics.cache_miss_total.labels(graph_id=request.graph_id).inc()
            
            # Load graph with retry and circuit breaker
            graph = self._load_graph_resilient(request.graph_id)
            
            # Validate nodes exist
            graph.validate_nodes_exist([request.start_node, request.goal_node])
            
            # Select algorithm
            algorithm = AlgorithmSelector.select(graph, request.algorithm_hint)
            algorithm_name = algorithm.name()
            
            # Log algorithm selection
            reason = "negative_weights" if graph.has_negative_weights() else "positive_weights"
            logger.info(
                "Algorithm selected",
                extra={
                    "request_id": request.request_id,
                    "algorithm": algorithm_name,
                    "reason": reason,
                }
            )
            metrics.algorithm_selection_total.labels(
                algorithm=algorithm_name,
                reason=reason
            ).inc()
            
            # Compute path with timeout
            compute_start = time.time()
            with timeout(request.timeout_ms / 1000.0, "path_computation"):
                path, cost = algorithm.compute(graph, request.start_node, request.goal_node)
            compute_time_ms = (time.time() - compute_start) * 1000
            
            # Validate result
            if request.validate_result:
                ResultValidator.validate_path(graph, path, cost)
            
            # Build response
            response = RouteResponse(
                request_id=request.request_id,
                status="success",
                path=path,
                cost=cost,
                metadata={
                    "algorithm_used": algorithm_name,
                    "computation_time_ms": round(compute_time_ms, 2),
                    "graph_nodes": len(list(graph.nodes())),
                    "graph_edges": len(list(graph.edges())),
                    "cache_hit": False,
                }
            )
            
            # Cache result
            self.cache.put(
                request.request_id,
                response,
                graph_id=request.graph_id,
                start_node=request.start_node,
                goal_node=request.goal_node,
            )
            
            # Metrics
            total_time_ms = (time.time() - start_time) * 1000
            metrics.requests_total.labels(
                graph_id=request.graph_id,
                algorithm=algorithm_name
            ).inc()
            metrics.success_total.labels(
                graph_id=request.graph_id,
                algorithm=algorithm_name
            ).inc()
            metrics.latency_ms.labels(
                graph_id=request.graph_id,
                algorithm=algorithm_name
            ).observe(total_time_ms)
            
            logger.info(
                "Route computed successfully",
                extra={
                    "request_id": request.request_id,
                    "algorithm": algorithm_name,
                    "path_length": len(path),
                    "cost": cost,
                    "time_ms": round(total_time_ms, 2),
                }
            )
            
            return response
            
        except NegativeCycleError as e:
            return self._error_response(
                request,
                "error",
                "NEGATIVE_CYCLE_DETECTED",
                str(e),
                {"cycle": e.cycle, "cycle_cost": e.cycle_cost}
            )
        
        except TimeoutError as e:
            metrics.timeout_total.labels(operation="path_computation").inc()
            return self._error_response(
                request,
                "timeout",
                "COMPUTATION_TIMEOUT",
                str(e)
            )
        
        except CircuitBreakerOpenError as e:
            return self._error_response(
                request,
                "error",
                "CIRCUIT_BREAKER_OPEN",
                str(e)
            )
        
        except GraphValidationError as e:
            metrics.validation_error_total.labels(reason="graph_validation").inc()
            return self._error_response(
                request,
                "error",
                "INVALID_GRAPH",
                str(e)
            )
        
        except ValidationError as e:
            metrics.validation_error_total.labels(reason="result_validation").inc()
            return self._error_response(
                request,
                "error",
                "INVALID_RESULT",
                str(e)
            )
        
        except ValueError as e:
            return self._error_response(
                request,
                "error",
                "INVALID_INPUT",
                str(e)
            )
        
        except Exception as e:
            logger.exception(
                "Unexpected error",
                extra={"request_id": request.request_id}
            )
            return self._error_response(
                request,
                "error",
                "INTERNAL_ERROR",
                f"Unexpected error: {type(e).__name__}"
            )
    
    @retry(
        max_attempts=3,
        initial_wait=1.0,
        backoff_multiplier=2.0,
        max_wait=10.0,
        exceptions=(IOError, TransientError)
    )
    def _load_graph_resilient(self, graph_id: str) -> Graph:
        """Load graph with retry and circuit breaker."""
        return self.circuit_breaker.call(self._graph_loader, graph_id)
    
    @staticmethod
    def _default_graph_loader(graph_id: str) -> Graph:
        """Default graph loader from file."""
        # In real implementation, this would load from database/service
        # For now, load from data directory
        path = f"data/{graph_id}.json"
        return Graph.from_json_file(path)
    
    @staticmethod
    def _error_response(
        request: RouteRequest,
        status: str,
        error_code: str,
        message: str,
        details: Optional[dict] = None
    ) -> RouteResponse:
        """Build error response."""
        logger.error(
            message,
            extra={"request_id": request.request_id, "error_code": error_code}
        )
        
        metrics.error_total.labels(
            graph_id=request.graph_id,
            error_type=error_code
        ).inc()
        
        return RouteResponse(
            request_id=request.request_id,
            status=status,
            error={
                "code": error_code,
                "message": message,
                "details": details or {}
            }
        )

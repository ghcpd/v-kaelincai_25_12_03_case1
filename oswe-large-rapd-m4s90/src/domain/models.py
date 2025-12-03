from __future__ import annotations

from enum import Enum
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field, validator


class Edge(BaseModel):
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    weight: float


class GraphData(BaseModel):
    edges: List[Edge]

    @validator('edges')
    def non_empty(cls, v):
        if not v:
            raise ValueError('edges must not be empty')
        return v

    def adjacency(self) -> Dict[str, Dict[str, float]]:
        adj: Dict[str, Dict[str, float]] = {}
        for e in self.edges:
            adj.setdefault(e.source, {})[e.target] = e.weight
            adj.setdefault(e.target, {})
        return adj

    def has_negative_edge(self) -> bool:
        return any(e.weight < 0 for e in self.edges)

    def nodes(self) -> List[str]:
        return list(self.adjacency().keys())


class PlanStatus(str, Enum):
    INIT = "init"
    VALIDATED = "validated"
    FETCH_GRAPH = "fetch_graph"
    PLANNING = "planning"
    SUCCESS = "success"
    FAILURE = "failure"
    COMPENSATED = "compensated"


class RouteRequest(BaseModel):
    request_id: str = Field(..., min_length=1, description="Idempotency key")
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    graph_id: Optional[str] = None
    graph: Optional[GraphData] = None
    timeout_seconds: Optional[float] = Field(None, gt=0)


class RouteResponse(BaseModel):
    request_id: str
    path: Optional[List[str]] = None
    cost: Optional[float] = None
    algorithm: Optional[str] = None
    status: PlanStatus
    error: Optional[str] = None
    retries: int = 0
    metrics: Dict[str, float] = Field(default_factory=dict)


class OutboxEvent(BaseModel):
    request_id: str
    status: PlanStatus
    path: Optional[List[str]] = None
    cost: Optional[float] = None
    error: Optional[str] = None


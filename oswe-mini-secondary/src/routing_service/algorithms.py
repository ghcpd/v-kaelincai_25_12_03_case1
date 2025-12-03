from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import heapq

from .graph import Graph


class ValidationError(ValueError):
    pass


def dijkstra_shortest_path(graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
    """
    Proper Dijkstra that rejects graphs with negative weights.
    Raises ValidationError if negative weight detected.
    """
    if graph.has_negative_weight():
        raise ValidationError("graph contains negative weight(s), Dijkstra is unsafe")

    dist: Dict[str, float] = {start: 0.0}
    prev: Dict[str, Optional[str]] = {start: None}
    heap: List[Tuple[float, str]] = [(0.0, start)]

    visited = set()

    while heap:
        cost, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)

        if node == goal:
            return _reconstruct_path(prev, goal), cost

        if cost > dist.get(node, float("inf")):
            continue

        for neighbor, weight in graph.neighbors(node).items():
            new_cost = cost + weight
            if new_cost < dist.get(neighbor, float("inf")):
                dist[neighbor] = new_cost
                prev[neighbor] = node
                heapq.heappush(heap, (new_cost, neighbor))

    raise LookupError(f"No path found from {start} to {goal}")


def bellman_ford_shortest_path(graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
    """
    Bellman-Ford algorithm: supports negative weights and detects negative cycles.
    Returns shortest path and cost or raises ValueError for negative cycles.
    """
    nodes = list(graph.nodes())
    dist: Dict[str, float] = {n: float("inf") for n in nodes}
    prev: Dict[str, Optional[str]] = {n: None for n in nodes}
    if start not in dist:
        raise LookupError("start node not in graph")
    dist[start] = 0.0

    # Relax edges |V|-1 times
    for _ in range(max(0, len(nodes) - 1)):
        updated = False
        for u in nodes:
            for v, w in graph.neighbors(u).items():
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    prev[v] = u
                    updated = True
        if not updated:
            break

    # Check for negative cycles
    for u in nodes:
        for v, w in graph.neighbors(u).items():
            if dist[u] + w < dist[v]:
                raise ValueError("Graph contains a negative-weight cycle")

    if dist.get(goal, float("inf")) == float("inf"):
        raise LookupError(f"No path found from {start} to {goal}")

    return _reconstruct_path(prev, goal), dist[goal]


def _reconstruct_path(prev: Dict[str, Optional[str]], goal: str) -> List[str]:
    path: List[str] = []
    n: Optional[str] = goal
    while n is not None:
        path.append(n)
        n = prev.get(n)
    return list(reversed(path))

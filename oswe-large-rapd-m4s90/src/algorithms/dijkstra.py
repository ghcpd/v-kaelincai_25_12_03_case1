from __future__ import annotations

from typing import Dict, List, Tuple
import heapq


class NegativeEdgeError(ValueError):
    pass


def has_negative_weight(adj: Dict[str, Dict[str, float]]) -> bool:
    return any(weight < 0 for _, nbrs in adj.items() for weight in nbrs.values())


def shortest_path(adj: Dict[str, Dict[str, float]], start: str, goal: str) -> Tuple[List[str], float]:
    """
    Dijkstra's algorithm with negative-edge validation and proper finalization.
    Raises NegativeEdgeError if any edge weight < 0.
    """
    if has_negative_weight(adj):
        raise NegativeEdgeError("graph contains negative edge; use bellman_ford")

    dist: Dict[str, float] = {start: 0.0}
    prev: Dict[str, str | None] = {start: None}
    heap: List[Tuple[float, str]] = [(0.0, start)]
    visited = set()

    while heap:
        cost, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)

        if node == goal:
            return _reconstruct(prev, goal), cost

        for neighbor, weight in adj.get(node, {}).items():
            new_cost = cost + weight
            if new_cost < dist.get(neighbor, float('inf')):
                dist[neighbor] = new_cost
                prev[neighbor] = node
                heapq.heappush(heap, (new_cost, neighbor))

    raise ValueError(f"No path found from {start} to {goal}")


def _reconstruct(prev: Dict[str, str | None], goal: str) -> List[str]:
    path: List[str] = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path))

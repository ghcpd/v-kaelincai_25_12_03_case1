from __future__ import annotations

from typing import Dict, List, Tuple


class NegativeCycleError(ValueError):
    pass


def shortest_path(adj: Dict[str, Dict[str, float]], start: str, goal: str) -> Tuple[List[str], float]:
    nodes: List[str] = list(adj.keys())
    dist: Dict[str, float] = {node: float('inf') for node in nodes}
    prev: Dict[str, str | None] = {node: None for node in nodes}
    dist[start] = 0.0

    edges: List[Tuple[str, str, float]] = [
        (u, v, w) for u, nbrs in adj.items() for v, w in nbrs.items()
    ]

    # Relax edges |V|-1 times
    for _ in range(len(nodes) - 1):
        updated = False
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                prev[v] = u
                updated = True
        if not updated:
            break

    # Detect negative cycles
    for u, v, w in edges:
        if dist[u] + w < dist[v]:
            raise NegativeCycleError("graph contains a negative-weight cycle")

    if dist[goal] == float('inf'):
        raise ValueError(f"No path found from {start} to {goal}")

    return _reconstruct(prev, goal), dist[goal]


def _reconstruct(prev: Dict[str, str | None], goal: str) -> List[str]:
    path: List[str] = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path))

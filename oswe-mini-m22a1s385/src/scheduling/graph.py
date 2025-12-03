from __future__ import annotations

from typing import Dict, Iterable, Tuple, List, Optional
import heapq

class Graph:
    def __init__(self) -> None:
        self._adj: Dict[str, Dict[str, float]] = {}

    def add_edge(self, source: str, target: str, weight: float) -> None:
        if source not in self._adj:
            self._adj[source] = {}
        self._adj[source][target] = weight
        if target not in self._adj:
            self._adj[target] = {}

    def neighbors(self, node: str) -> Dict[str, float]:
        return self._adj.get(node, {})

    def edges(self):
        for s, d in self._adj.items():
            for t, w in d.items():
                yield (s, t, w)

    @classmethod
    def from_edge_list(cls, edges: Iterable[Tuple[str, str, float]]) -> "Graph":
        g = Graph()
        for s, t, w in edges:
            g.add_edge(s, t, w)
        return g


def dijkstra_shortest_path(graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
    # Correct Dijkstra: mark nodes finalized when popped from heap
    dist: Dict[str, float] = {start: 0.0}
    prev: Dict[str, Optional[str]] = {start: None}
    heap: List[Tuple[float, str]] = [(0.0, start)]
    finalized = set()

    while heap:
        cost, node = heapq.heappop(heap)
        if node in finalized:
            continue
        finalized.add(node)
        if node == goal:
            return _reconstruct_path(prev, goal), cost
        for neighbor, weight in graph.neighbors(node).items():
            new_cost = cost + weight
            if new_cost < dist.get(neighbor, float('inf')):
                dist[neighbor] = new_cost
                prev[neighbor] = node
                heapq.heappush(heap, (new_cost, neighbor))
    raise ValueError(f"No path found from {start} to {goal}")


def bellman_ford_shortest_path(graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
    # Bellman-Ford algorithm to support negative weights
    nodes = list(graph._adj.keys())
    dist: Dict[str, float] = {n: float('inf') for n in nodes}
    prev: Dict[str, Optional[str]] = {n: None for n in nodes}
    dist[start] = 0.0

    for _ in range(len(nodes) - 1):
        updated = False
        for u, v, w in graph.edges():
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                prev[v] = u
                updated = True
        if not updated:
            break

    # Detect negative cycle
    for u, v, w in graph.edges():
        if dist[u] + w < dist[v]:
            raise ValueError('negative cycle detected')

    if dist.get(goal, float('inf')) == float('inf'):
        raise ValueError(f"No path found from {start} to {goal}")
    return _reconstruct_path(prev, goal), dist[goal]


def _reconstruct_path(prev: Dict[str, Optional[str]], goal: str) -> List[str]:
    path: List[str] = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path))

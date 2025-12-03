from typing import Dict, Iterable, Tuple, List


class Graph:
    """Simple directed weighted graph."""

    def __init__(self) -> None:
        self._adj: Dict[str, Dict[str, float]] = {}

    def add_edge(self, source: str, target: str, weight: float) -> None:
        if source not in self._adj:
            self._adj[source] = {}
        self._adj[source][target] = float(weight)
        if target not in self._adj:
            self._adj[target] = {}

    def neighbors(self, node: str):
        return self._adj.get(node, {})

    def nodes(self) -> Iterable[str]:
        return list(self._adj.keys())

    @staticmethod
    def from_edge_list(edges: Iterable[Tuple[str, str, float]]):
        g = Graph()
        for s, t, w in edges:
            g.add_edge(s, t, w)
        return g

    def has_negative_weight(self) -> bool:
        for src in self._adj:
            for _, w in self._adj[src].items():
                if w < 0:
                    return True
        return False

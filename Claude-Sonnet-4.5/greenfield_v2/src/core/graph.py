"""Graph model with validation for v2 routing system."""
from __future__ import annotations

from typing import Dict, Iterable, Tuple, List, Set
import json
import hashlib


class GraphValidationError(Exception):
    """Raised when graph validation fails."""
    pass


class Graph:
    """Directed weighted graph with validation support."""

    def __init__(self) -> None:
        self._adj: Dict[str, Dict[str, float]] = {}
        self._hash: str = ""

    def add_edge(self, source: str, target: str, weight: float) -> None:
        """Add edge with validation."""
        if not isinstance(weight, (int, float)):
            raise GraphValidationError(f"Weight must be numeric, got {type(weight)}")
        
        if source not in self._adj:
            self._adj[source] = {}
        self._adj[source][target] = weight
        
        if target not in self._adj:
            self._adj[target] = {}

    def neighbors(self, node: str) -> Dict[str, float]:
        """Get neighbors of a node."""
        return self._adj.get(node, {})

    def nodes(self) -> Iterable[str]:
        """Get all nodes in the graph."""
        return self._adj.keys()

    def edges(self) -> Iterable[Tuple[str, str, float]]:
        """Get all edges as (source, target, weight) tuples."""
        for source, neighbors in self._adj.items():
            for target, weight in neighbors.items():
                yield (source, target, weight)

    def has_negative_weights(self) -> bool:
        """Check if graph contains any negative weights."""
        return any(weight < 0 for _, _, weight in self.edges())

    def min_weight(self) -> float:
        """Get minimum edge weight in graph."""
        weights = [weight for _, _, weight in self.edges()]
        return min(weights) if weights else 0.0

    def compute_hash(self) -> str:
        """Compute MD5 hash of graph structure for cache keying."""
        if self._hash:
            return self._hash
        
        # Sort edges for consistent hashing
        edges_sorted = sorted(self.edges())
        edge_str = str(edges_sorted)
        self._hash = hashlib.md5(edge_str.encode()).hexdigest()
        return self._hash

    @staticmethod
    def from_edge_list(edges: Iterable[Tuple[str, str, float]]) -> "Graph":
        """Create graph from edge list."""
        g = Graph()
        for src, dst, w in edges:
            g.add_edge(src, dst, w)
        return g

    @classmethod
    def from_json_file(cls, path: str) -> "Graph":
        """Load graph from JSON file.
        
        Expected format:
        {
          "edges": [
            {"source": "A", "target": "B", "weight": 5},
            ...
          ]
        }
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "edges" not in data:
            raise GraphValidationError("JSON must contain 'edges' array")
        
        edges: List[Tuple[str, str, float]] = []
        for i, e in enumerate(data["edges"]):
            if not all(k in e for k in ["source", "target", "weight"]):
                raise GraphValidationError(f"Edge {i} missing required fields")
            edges.append((e["source"], e["target"], e["weight"]))
        
        return cls.from_edge_list(edges)

    def validate_nodes_exist(self, nodes: List[str]) -> None:
        """Validate that nodes exist in graph."""
        graph_nodes = set(self.nodes())
        for node in nodes:
            if node not in graph_nodes:
                raise GraphValidationError(f"Node '{node}' not found in graph")

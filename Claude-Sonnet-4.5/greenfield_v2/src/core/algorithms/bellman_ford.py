"""Bellman-Ford algorithm implementation."""
from typing import Dict, List, Tuple, Optional

from .base import PathAlgorithm
from ..graph import Graph


class NegativeCycleError(ValueError):
    """Raised when a negative weight cycle is detected."""
    def __init__(self, cycle: List[str], cycle_cost: float):
        self.cycle = cycle
        self.cycle_cost = cycle_cost
        super().__init__(
            f"Negative cycle detected: {' -> '.join(cycle)} with cost {cycle_cost}"
        )


class BellmanFordAlgorithm(PathAlgorithm):
    """
    Bellman-Ford shortest path algorithm.
    
    Supports negative edge weights and detects negative cycles.
    Time complexity: O(VE)
    """
    
    def compute(self, graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
        """
        Compute shortest path using Bellman-Ford algorithm.
        
        Works with negative weights but detects negative cycles.
        """
        graph.validate_nodes_exist([start, goal])
        
        nodes = list(graph.nodes())
        n = len(nodes)
        
        # Initialize distances
        dist: Dict[str, float] = {node: float("inf") for node in nodes}
        dist[start] = 0.0
        prev: Dict[str, Optional[str]] = {node: None for node in nodes}
        
        # Relax edges V-1 times
        for _ in range(n - 1):
            updated = False
            for source, target, weight in graph.edges():
                if dist[source] + weight < dist[target]:
                    dist[target] = dist[source] + weight
                    prev[target] = source
                    updated = True
            
            # Early termination if no updates
            if not updated:
                break
        
        # Check for negative cycles
        cycle_info = self._detect_negative_cycle(graph, dist)
        if cycle_info:
            cycle, cycle_cost = cycle_info
            raise NegativeCycleError(cycle, cycle_cost)
        
        # Check if goal is reachable
        if dist[goal] == float("inf"):
            raise ValueError(f"No path exists from {start} to {goal}")
        
        return self._reconstruct_path(prev, goal), dist[goal]
    
    def name(self) -> str:
        return "bellman_ford"
    
    @staticmethod
    def _detect_negative_cycle(
        graph: Graph, 
        dist: Dict[str, float]
    ) -> Optional[Tuple[List[str], float]]:
        """
        Detect negative cycle by attempting one more relaxation.
        
        Returns:
            Tuple of (cycle_path, cycle_cost) if cycle detected, else None
        """
        for source, target, weight in graph.edges():
            if dist[source] + weight < dist[target]:
                # Negative cycle detected, reconstruct it
                cycle = [target]
                visited = {target}
                current = source
                
                # Walk backwards to find cycle
                while current not in visited and len(cycle) < len(dist):
                    cycle.append(current)
                    visited.add(current)
                    # Find predecessor (any edge that could have relaxed to current)
                    for s, t, w in graph.edges():
                        if t == current and dist[s] + w == dist[current]:
                            current = s
                            break
                
                # Calculate cycle cost
                cycle_cost = 0.0
                for i in range(len(cycle) - 1):
                    for s, t, w in graph.edges():
                        if s == cycle[i] and t == cycle[i + 1]:
                            cycle_cost += w
                            break
                
                return (list(reversed(cycle)), cycle_cost)
        
        return None
    
    @staticmethod
    def _reconstruct_path(prev: Dict[str, Optional[str]], goal: str) -> List[str]:
        """Reconstruct path from predecessor map."""
        path: List[str] = []
        node = goal
        while node is not None:
            path.append(node)
            node = prev.get(node)
        return list(reversed(path))

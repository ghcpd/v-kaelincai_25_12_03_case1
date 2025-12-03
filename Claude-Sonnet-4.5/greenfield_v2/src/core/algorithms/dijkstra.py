"""Dijkstra's algorithm implementation (corrected)."""
from typing import Dict, List, Tuple, Optional
import heapq

from .base import PathAlgorithm
from ..graph import Graph


class DijkstraAlgorithm(PathAlgorithm):
    """
    Dijkstra's shortest path algorithm.
    
    Correct implementation that marks nodes as visited when popped from heap,
    not when first discovered. Only works with non-negative edge weights.
    """
    
    def compute(self, graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
        """
        Compute shortest path using Dijkstra's algorithm.
        
        Precondition: All edge weights must be non-negative.
        """
        # Validate preconditions
        if graph.has_negative_weights():
            raise ValueError(
                f"Dijkstra requires non-negative weights. "
                f"Minimum weight: {graph.min_weight()}"
            )
        
        graph.validate_nodes_exist([start, goal])
        
        # Distances and predecessor tracking
        dist: Dict[str, float] = {start: 0.0}
        prev: Dict[str, Optional[str]] = {start: None}
        
        # Min-heap: (cost, node)
        heap: List[Tuple[float, str]] = [(0.0, start)]
        
        # CORRECTED: visited set populated when node is finalized (popped)
        visited: set = set()
        
        while heap:
            cost, node = heapq.heappop(heap)
            
            # Skip if already visited (stale heap entry)
            if node in visited:
                continue
            
            # Mark as visited (finalized)
            visited.add(node)
            
            # Goal reached
            if node == goal:
                return self._reconstruct_path(prev, goal), cost
            
            # Relax neighbors
            for neighbor, weight in graph.neighbors(node).items():
                if neighbor in visited:
                    continue
                
                new_cost = cost + weight
                if new_cost < dist.get(neighbor, float("inf")):
                    dist[neighbor] = new_cost
                    prev[neighbor] = node
                    heapq.heappush(heap, (new_cost, neighbor))
        
        raise ValueError(f"No path exists from {start} to {goal}")
    
    def name(self) -> str:
        return "dijkstra"
    
    @staticmethod
    def _reconstruct_path(prev: Dict[str, Optional[str]], goal: str) -> List[str]:
        """Reconstruct path from predecessor map."""
        path: List[str] = []
        node = goal
        while node is not None:
            path.append(node)
            node = prev.get(node)
        return list(reversed(path))

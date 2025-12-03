"""Algorithm selector - chooses optimal algorithm based on graph properties."""
from .base import PathAlgorithm
from .dijkstra import DijkstraAlgorithm
from .bellman_ford import BellmanFordAlgorithm
from ..graph import Graph


class AlgorithmSelector:
    """Selects the optimal shortest path algorithm based on graph properties."""
    
    @staticmethod
    def select(graph: Graph, algorithm_hint: str = "auto") -> PathAlgorithm:
        """
        Select algorithm based on graph properties.
        
        Args:
            graph: The graph to analyze
            algorithm_hint: User preference ("auto", "dijkstra", "bellman_ford")
            
        Returns:
            Selected PathAlgorithm instance
            
        Raises:
            ValueError: If algorithm_hint is invalid
        """
        if algorithm_hint == "dijkstra":
            return DijkstraAlgorithm()
        elif algorithm_hint == "bellman_ford":
            return BellmanFordAlgorithm()
        elif algorithm_hint == "auto":
            # Automatic selection based on graph properties
            if graph.has_negative_weights():
                return BellmanFordAlgorithm()
            else:
                return DijkstraAlgorithm()
        else:
            raise ValueError(
                f"Unknown algorithm: {algorithm_hint}. "
                f"Supported: auto, dijkstra, bellman_ford"
            )

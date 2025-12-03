"""Base class for path algorithms."""
from abc import ABC, abstractmethod
from typing import List, Tuple
from ..graph import Graph


class PathAlgorithm(ABC):
    """Abstract base class for shortest path algorithms."""
    
    @abstractmethod
    def compute(self, graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
        """
        Compute shortest path from start to goal.
        
        Returns:
            Tuple of (path, cost) where path is list of node IDs
            
        Raises:
            ValueError: If no path exists or algorithm preconditions violated
        """
        pass
    
    @abstractmethod
    def name(self) -> str:
        """Return algorithm name for logging/metrics."""
        pass

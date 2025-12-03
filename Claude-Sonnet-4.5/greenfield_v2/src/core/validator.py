"""Result validator - verifies path correctness."""
from typing import List
from .graph import Graph


class ValidationError(Exception):
    """Raised when result validation fails."""
    pass


class ResultValidator:
    """Validates computed paths against graph."""
    
    @staticmethod
    def validate_path(graph: Graph, path: List[str], expected_cost: float) -> None:
        """
        Validate that path is valid and cost matches.
        
        Args:
            graph: The graph
            path: Computed path as list of node IDs
            expected_cost: Claimed total cost
            
        Raises:
            ValidationError: If path is invalid or cost mismatch
        """
        if len(path) < 2:
            raise ValidationError("Path must contain at least 2 nodes")
        
        # Verify all edges exist and compute actual cost
        actual_cost = 0.0
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            
            neighbors = graph.neighbors(source)
            if target not in neighbors:
                raise ValidationError(
                    f"Edge {source} -> {target} does not exist in graph"
                )
            
            actual_cost += neighbors[target]
        
        # Verify cost matches (with floating point tolerance)
        if abs(actual_cost - expected_cost) > 1e-6:
            raise ValidationError(
                f"Cost mismatch: expected {expected_cost}, actual {actual_cost}"
            )

from routing_service.graph import Graph
from routing_service.algorithms import dijkstra_shortest_path, bellman_ford_shortest_path, ValidationError


def make_negative_graph():
    edges = [
        ("A", "B", 5),
        ("A", "C", 2),
        ("C", "D", 1),
        ("D", "F", -3),
        ("F", "B", 1),
        ("A", "E", 1),
        ("E", "B", 6),
    ]
    return Graph.from_edge_list(edges)


def test_dijkstra_rejects_negative_weights():
    g = make_negative_graph()
    try:
        # dijkstra should reject graphs with negative weights
        dijkstra_shortest_path(g, "A", "B")
        assert False, "Expected ValidationError"
    except ValidationError:
        pass


def test_bellman_ford_finds_optimal():
    g = make_negative_graph()
    path, cost = bellman_ford_shortest_path(g, "A", "B")
    assert path == ["A", "C", "D", "F", "B"]
    assert cost == 1.0


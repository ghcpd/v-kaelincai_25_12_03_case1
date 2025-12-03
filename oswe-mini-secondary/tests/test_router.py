import time
from routing_service.graph import Graph
from routing_service.core import Router, RouterState
from routing_service import algorithms


def mk_graph():
    edges = [
        ("A", "B", 5),
        ("A", "C", 2),
        ("C", "D", 1),
        ("D", "F", -3),
        ("F", "B", 1),
    ]
    return Graph.from_edge_list(edges)


def test_router_auto_switches_to_bellman_ford():
    logs = []
    g = mk_graph()
    r = Router(g, logger=lambda **kw: logs.append(kw))

    res = r.route("A", "B", idempotency_key="k1")
    assert res["cost"] == 1.0
    assert res["algorithm"] == "bellman-ford"
    assert r.appointments["k1"]["state"] == RouterState.SUCCEEDED


def test_idempotency_prevents_double_processing():
    g = mk_graph()
    r = Router(g)
    k = "idem-key"
    r.route("A", "B", idempotency_key=k)
    outbox_count_first = len(r.outbox)

    # second call should return cached result and not add new outbox event
    r.route("A", "B", idempotency_key=k)
    assert len(r.outbox) == outbox_count_first


def test_timeout_propagation(monkeypatch):
    g = mk_graph()
    r = Router(g)

    # monkeypatch a long-running bellman_ford to simulate a timeout
    def long_running(*a, **k):
        time.sleep(0.2)
        return ([], 0.0)

    monkeypatch.setattr(algorithms, "bellman_ford_shortest_path", long_running)

    # short timeout forces a TimeoutError
    try:
        r.route("A", "B", algorithm="bellman-ford", timeout_seconds=0.01)
        assert False, "expected a TimeoutError"
    except TimeoutError:
        pass


def test_outbox_on_failure(monkeypatch):
    g = mk_graph()
    r = Router(g)

    def fail(*a, **k):
        raise RuntimeError("simulated transient failure")

    monkeypatch.setattr(algorithms, "bellman_ford_shortest_path", fail)

    try:
        r.route("A", "B", algorithm="bellman-ford", idempotency_key="fail-1")
        assert False, "expected RuntimeError"
    except RuntimeError:
        # ensure a failed outbox event exists
        assert any(ev["event"].endswith("failed") for ev in r.outbox.values())


def test_retry_and_idempotency_on_transient_failure(monkeypatch):
    g = mk_graph()
    r = Router(g)

    # Two-phase: first call fails (transient), second call succeeds
    called = {"count": 0}

    def flaky(*a, **k):
        called["count"] += 1
        if called["count"] == 1:
            raise RuntimeError("transient")
        return (["A","C","D","F","B"], 1.0)

    monkeypatch.setattr(algorithms, "bellman_ford_shortest_path", flaky)

    key = "retries-key"
    # first attempt => fails and records error
    try:
        r.route("A", "B", algorithm="bellman-ford", idempotency_key=key)
    except RuntimeError:
        pass

    # second attempt => succeed reusing same idempotency key
    res = r.route("A", "B", algorithm="bellman-ford", idempotency_key=key)
    assert res["cost"] == 1.0
    # ensure final appointment state is succeeded
    assert r.appointments[key]["state"] == RouterState.SUCCEEDED


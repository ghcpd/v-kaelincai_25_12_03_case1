import pytest
from scheduling.graph import Graph
from scheduling.service import AppointmentService, InMemoryStore, ExternalCalendarError
from mocks.external_calendar import MockCalendarClient


def build_graph_negative():
    # Graph with a negative weight but no negative cycle
    g = Graph()
    edges = [
        ('A','B',5),
        ('A','C',2),
        ('C','D',1),
        ('D','F',-3),
        ('F','B',1),
    ]
    for s,t,w in edges:
        g.add_edge(s,t,w)
    return g


def build_graph_negative_cycle():
    g = Graph()
    edges = [
        ('A','B',1),
        ('B','C',-5),
        ('C','A',1),
    ]
    for s,t,w in edges:
        g.add_edge(s,t,w)
    return g


def test_healthy_path_and_outbox_publish():
    g = Graph()
    g.add_edge('A','B',1)
    serv = AppointmentService(store=InMemoryStore(), calendar_client=MockCalendarClient())
    appt = serv.create_appointment('key-1','cust-1', {'start_time':1,'end_time':2}, g, 'A','B')
    assert appt['path'] == ['A','B']
    assert len(serv.store.outbox) == 1
    serv.process_outbox()
    assert len(serv.store.outbox) == 0


def test_negative_weight_bellman_ford():
    g = build_graph_negative()
    serv = AppointmentService(store=InMemoryStore(), calendar_client=MockCalendarClient())
    appt = serv.create_appointment('key-2','cust-1', {'start_time':1,'end_time':2}, g, 'A','B')
    assert appt['path'] == ['A','C','D','F','B']
    assert appt['cost'] == pytest.approx(1.0)


def test_negative_cycle_rejected():
    g = build_graph_negative_cycle()
    serv = AppointmentService(store=InMemoryStore(), calendar_client=MockCalendarClient())
    with pytest.raises(ValueError, match='negative'):
        serv.create_appointment('key-3','cust-1', {'start_time':1,'end_time':2}, g, 'A','C')


def test_idempotency_key_prevents_duplicates():
    g = Graph()
    g.add_edge('A','B',1)
    store = InMemoryStore()
    serv = AppointmentService(store=store, calendar_client=MockCalendarClient())
    a1 = serv.create_appointment('key-dup','cust-1', {'start_time':1,'end_time':2}, g, 'A','B')
    a2 = serv.create_appointment('key-dup','cust-1', {'start_time':1,'end_time':2}, g, 'A','B')
    assert a1['id'] == a2['id']
    assert len(store.appointments) == 1
    assert len(store.outbox) == 1


def test_retry_backoff_and_dead_letter():
    g = Graph()
    g.add_edge('A','B',1)
    # fail first two attempts then succeed
    client = MockCalendarClient(fail_until_attempts=2)
    store = InMemoryStore()
    serv = AppointmentService(store=store, calendar_client=client)
    serv.create_appointment('key-retry','cust-1', {'start_time':1,'end_time':2}, g, 'A','B')
    # first processing attempt increments attempts
    serv.process_outbox(max_attempts=5)
    assert client.attempts >= 1
    # eventually outbox empty because client will succeed
    assert len(store.outbox) == 0


def test_outbox_dead_letter_after_max_attempts():
    g = Graph()
    g.add_edge('A','B',1)
    # client fails forever
    client = MockCalendarClient(fail_until_attempts=100)
    store = InMemoryStore()
    serv = AppointmentService(store=store, calendar_client=client)
    serv.create_appointment('key-dead','cust-1', {'start_time':1,'end_time':2}, g, 'A','B')
    serv.process_outbox(max_attempts=2)
    # outbox removed after exceeding max attempts
    assert len(store.outbox) == 0


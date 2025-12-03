from __future__ import annotations
from typing import Dict, Any, Optional
import uuid
import time
from .graph import Graph, bellman_ford_shortest_path, dijkstra_shortest_path

class IdempotencyError(Exception):
    pass

class ExternalCalendarError(Exception):
    pass

class InMemoryStore:
    def __init__(self):
        self.appointments: Dict[str, Dict[str, Any]] = {}
        self.idemp_keys: Dict[str, str] = {}
        self.outbox: list[Dict[str, Any]] = []

class AppointmentService:
    def __init__(self, store: Optional[InMemoryStore] = None, calendar_client=None):
        self.store = store or InMemoryStore()
        self.calendar_client = calendar_client

    def _check_idempotency(self, idemp_key: str) -> Optional[Dict[str, Any]]:
        if idemp_key in self.store.idemp_keys:
            appt_id = self.store.idemp_keys[idemp_key]
            return self.store.appointments.get(appt_id)
        return None

    def create_appointment(self, idempotency_key: str, customer_id: str, slot: Dict[str, Any], graph: Graph, start_node: str, end_node: str):
        existing = self._check_idempotency(idempotency_key)
        if existing:
            return existing
        appt_id = str(uuid.uuid4())
        # Basic validation
        if slot['start_time'] >= slot['end_time']:
            raise ValueError('invalid slot')
        # Determine shortest path: if graph has negative weights use Bellman-Ford
        has_negative = any(w < 0 for _,_,w in graph.edges())
        if has_negative:
            # Use Bellman-Ford; if negative cycle raise
            path, cost = bellman_ford_shortest_path(graph, start_node, end_node)
        else:
            path, cost = dijkstra_shortest_path(graph, start_node, end_node)

        appt = {
            'id': appt_id,
            'customer_id': customer_id,
            'slot': slot,
            'path': path,
            'cost': cost,
            'state': 'SCHEDULED',
            'created_at': time.time(),
        }
        self.store.appointments[appt_id] = appt
        self.store.idemp_keys[idempotency_key] = appt_id
        # Write to outbox for notification/external reservation
        self.store.outbox.append({'topic': 'appointment_created', 'payload': appt, 'attempts': 0})
        return appt

    def process_outbox(self, max_attempts=3):
        # Worker: try to call calendar client and publish events with in-loop retries
        for item in list(self.store.outbox):
            while item['attempts'] < max_attempts:
                try:
                    if self.calendar_client:
                        self.calendar_client.reserve(item['payload'])
                    # success -> publish event (in tests we append to results)
                    item['published'] = True
                    try:
                        self.store.outbox.remove(item)
                    except ValueError:
                        pass
                    break
                except ExternalCalendarError:
                    item['attempts'] += 1
                    # exponential backoff with jitter (small in tests)
                    import time, random
                    backoff = 0.01 * (2 ** item['attempts'])
                    time.sleep(backoff + random.random() * 0.001)
                    continue
            else:
                # exceeded max attempts: dead-letter (remove from outbox)
                try:
                    self.store.outbox.remove(item)
                except ValueError:
                    pass

    def get_appointment(self, appt_id: str):
        return self.store.appointments.get(appt_id)

import time

class MockScheduler:
    """Simple mock scheduler that simulates delivery of routing events.

    Methods are synchronous for tests; callers can inspect `events` for delivered items.
    """

    def __init__(self, delay=0.0, should_fail=False):
        self.delay = delay
        self.should_fail = should_fail
        self.events = []

    def deliver(self, payload: dict):
        if self.delay:
            time.sleep(self.delay)
        if self.should_fail:
            raise RuntimeError("downstream failure")
        self.events.append(payload)
        return True

from scheduling.service import ExternalCalendarError

class MockCalendarClient:
    def __init__(self, fail_until_attempts=0, delay=0):
        self.attempts = 0
        self.fail_until_attempts = fail_until_attempts
        self.delay = delay

    def reserve(self, appointment_payload):
        self.attempts += 1
        if self.delay:
            import time
            time.sleep(self.delay)
        if self.attempts <= self.fail_until_attempts:
            raise ExternalCalendarError('transient failure')
        return {'status': 'reserved', 'reservation_id': 'res-' + appointment_payload['id']}


# Reuse same type for clarity
ExternalCalendarError = ExternalCalendarError
import os
import pytest
import logging
from fastapi.testclient import TestClient
from raptor_secondary.infra.logging import configure_logging
from raptor_secondary.infra.config import DEFAULT_CONFIG, AppConfig
from raptor_secondary.mocks.api import app as mock_app
from raptor_secondary.adapters.external_provider import ProviderError, ProviderTimeout
from raptor_secondary.infra.repositories import InMemoryAppointmentRepository, InMemoryOutboxRepository
from raptor_secondary.services.appointment_service import AppointmentService


@pytest.fixture(scope="session", autouse=True)
def _configure_logging():
    os.environ.setdefault("RAPTOR_LOG_FILE", os.path.join(os.getcwd(), "logs", "log_post.txt"))
    configure_logging()
    import logging
    logging.getLogger().info("logging_configured_test")


@pytest.fixture(scope="session")
def test_client():
    return TestClient(mock_app)


@pytest.fixture
def provider_client(test_client):
    # Wrap TestClient to provide the same interface as HttpExternalProviderClient
    class _Client:
        def schedule(self, payload: dict, timeout: float):
            # Simulate timeout without waiting when mode indicates
            if payload.get("mode") == "timeout":
                raise ProviderTimeout("simulated timeout")
            try:
                resp = test_client.post("/api/v2/schedule", json=payload)
                resp.raise_for_status()
            except Exception as e:
                # Starlette TestClient doesn't raise TimeoutException; map HTTP errors
                raise ProviderError(str(e)) from e
            data = resp.json()
            return data.get("status"), data

        def cancel(self, payload: dict, timeout: float):
            try:
                resp = test_client.post("/api/v2/cancel", json=payload)
                resp.raise_for_status()
            except Exception as e:
                raise ProviderError(str(e)) from e
            data = resp.json()
            return data.get("status"), data
    return _Client()


@pytest.fixture
def repositories():
    return {
        "appointments": InMemoryAppointmentRepository(),
        "outbox": InMemoryOutboxRepository(),
    }


@pytest.fixture
def config() -> AppConfig:
    # Use default config suitable for tests (small timeouts/backoff)
    return DEFAULT_CONFIG


@pytest.fixture
def service(provider_client, repositories, config):
    return AppointmentService(
        provider_client=provider_client,
        appointments=repositories["appointments"],
        outbox=repositories["outbox"],
        config=config,
    )


@pytest.fixture(autouse=True)
def flush_logs():
    yield
    for handler in logging.getLogger().handlers:
        try:
            handler.flush()
        except Exception:
            pass

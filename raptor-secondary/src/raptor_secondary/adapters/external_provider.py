from __future__ import annotations

from typing import Protocol, Tuple
import httpx


class ProviderError(Exception):
    pass


class ProviderTimeout(Exception):
    pass


class ExternalProviderClient(Protocol):
    def schedule(self, payload: dict, timeout: float) -> Tuple[str, dict]:
        ...

    def cancel(self, payload: dict, timeout: float) -> Tuple[str, dict]:
        ...


class HttpExternalProviderClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def schedule(self, payload: dict, timeout: float) -> Tuple[str, dict]:
        try:
            resp = httpx.post(f"{self.base_url}/api/v2/schedule", json=payload, timeout=timeout)
            resp.raise_for_status()
        except httpx.TimeoutException as e:
            raise ProviderTimeout(str(e)) from e
        except httpx.HTTPError as e:
            raise ProviderError(str(e)) from e
        data = resp.json()
        return data.get("status"), data

    def cancel(self, payload: dict, timeout: float) -> Tuple[str, dict]:
        try:
            resp = httpx.post(f"{self.base_url}/api/v2/cancel", json=payload, timeout=timeout)
            resp.raise_for_status()
        except httpx.TimeoutException as e:
            raise ProviderTimeout(str(e)) from e
        except httpx.HTTPError as e:
            raise ProviderError(str(e)) from e
        data = resp.json()
        return data.get("status"), data

"""HTTP client for calling provider-sim with circuit breaker integration."""

import os
import logging
import httpx
from shared.correlation import get_correlation_id
from services.circuit_breaker import CircuitBreaker, ProviderUnavailableError

logger = logging.getLogger("payrail.provider_client")

PROVIDER_SIM_URL = os.environ.get("PROVIDER_SIM_URL", "http://provider-sim:8028")


class ProviderError(Exception):
    def __init__(self, provider_id: str, detail: str):
        self.provider_id = provider_id
        self.detail = detail
        super().__init__(f"Provider {provider_id} error: {detail}")


class ProviderTimeoutError(ProviderError):
    def __init__(self, provider_id: str):
        super().__init__(provider_id, "Request timed out")


class ProviderClient:

    async def authorize(self, provider_id: str, payment_id: str, amount: int,
                        currency: str, pan: str, expiry: str, merchant_id: str) -> dict:
        cb = CircuitBreaker(provider_id)
        if not cb.can_execute():
            raise ProviderUnavailableError(provider_id)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{PROVIDER_SIM_URL}/providers/{provider_id}/authorize",
                    json={
                        "payment_id": payment_id,
                        "amount": amount,
                        "currency": currency,
                        "pan": pan,
                        "expiry": expiry,
                        "merchant_id": merchant_id,
                        "correlation_id": get_correlation_id(),
                    },
                    headers={"X-Correlation-Id": get_correlation_id()},
                    timeout=10.0,
                )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    cb.record_success()
                else:
                    cb.record_failure()
                return data
            else:
                cb.record_failure()
                raise ProviderError(provider_id, resp.text)
        except httpx.TimeoutException:
            cb.record_failure()
            raise ProviderTimeoutError(provider_id)
        except (httpx.ConnectError, httpx.ReadError) as e:
            cb.record_failure()
            raise ProviderError(provider_id, str(e))

    async def capture(self, provider_id: str, payment_id: str,
                      provider_ref: str, amount: int) -> dict:
        cb = CircuitBreaker(provider_id)
        if not cb.can_execute():
            raise ProviderUnavailableError(provider_id)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{PROVIDER_SIM_URL}/providers/{provider_id}/capture",
                    json={
                        "payment_id": payment_id,
                        "provider_ref": provider_ref,
                        "amount": amount,
                        "correlation_id": get_correlation_id(),
                    },
                    headers={"X-Correlation-Id": get_correlation_id()},
                    timeout=10.0,
                )
            if resp.status_code == 200:
                cb.record_success()
                return resp.json()
            else:
                cb.record_failure()
                raise ProviderError(provider_id, resp.text)
        except httpx.TimeoutException:
            cb.record_failure()
            raise ProviderTimeoutError(provider_id)

    async def refund(self, provider_id: str, payment_id: str,
                     provider_ref: str, amount: int) -> dict:
        cb = CircuitBreaker(provider_id)
        if not cb.can_execute():
            raise ProviderUnavailableError(provider_id)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{PROVIDER_SIM_URL}/providers/{provider_id}/refund",
                    json={
                        "payment_id": payment_id,
                        "provider_ref": provider_ref,
                        "amount": amount,
                        "correlation_id": get_correlation_id(),
                    },
                    headers={"X-Correlation-Id": get_correlation_id()},
                    timeout=10.0,
                )
            if resp.status_code == 200:
                cb.record_success()
                return resp.json()
            else:
                cb.record_failure()
                raise ProviderError(provider_id, resp.text)
        except httpx.TimeoutException:
            cb.record_failure()
            raise ProviderTimeoutError(provider_id)

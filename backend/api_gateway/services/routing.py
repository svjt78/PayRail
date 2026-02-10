"""Routing engine - selects payment provider based on rules and health."""

import os
import logging
from typing import Optional
from shared.models import CircuitState
from services.circuit_breaker import CircuitBreaker

logger = logging.getLogger("payrail.routing")

DEFAULT_PROVIDER = os.environ.get("DEFAULT_PROVIDER", "providerA")
FAILOVER_PROVIDER = os.environ.get("FAILOVER_PROVIDER", "providerB")

# Cost table (percentage fees)
COST_TABLE = {
    "providerA": 2.9,
    "providerB": 2.5,
}

# Country routing rules
COUNTRY_ROUTES = {
    "DE": "providerB",
    "FR": "providerB",
    "GB": "providerB",
    "JP": "providerB",
    "US": "providerA",
    "CA": "providerA",
    "AU": "providerA",
}

# Amount thresholds
HIGH_VALUE_THRESHOLD = 10000  # cents ($100)
HIGH_VALUE_PROVIDER = "providerB"


class RoutingEngine:

    def select_provider(
        self,
        amount: int,
        currency: str = "USD",
        country: Optional[str] = None,
        preferred_provider: Optional[str] = None,
    ) -> str:
        # 1. If explicitly preferred and available, use it
        if preferred_provider:
            cb = CircuitBreaker(preferred_provider)
            if cb.can_execute():
                return preferred_provider

        # 2. Country-based routing
        if country and country in COUNTRY_ROUTES:
            provider = COUNTRY_ROUTES[country]
            cb = CircuitBreaker(provider)
            if cb.can_execute():
                logger.info(f"Routing to {provider} based on country {country}")
                return provider

        # 3. Amount-based routing
        if amount >= HIGH_VALUE_THRESHOLD:
            cb = CircuitBreaker(HIGH_VALUE_PROVIDER)
            if cb.can_execute():
                logger.info(f"Routing to {HIGH_VALUE_PROVIDER} for high-value payment ({amount})")
                return HIGH_VALUE_PROVIDER

        # 4. Default provider
        cb_default = CircuitBreaker(DEFAULT_PROVIDER)
        if cb_default.can_execute():
            return DEFAULT_PROVIDER

        # 5. Failover
        cb_failover = CircuitBreaker(FAILOVER_PROVIDER)
        if cb_failover.can_execute():
            logger.warning(f"Failing over to {FAILOVER_PROVIDER}")
            return FAILOVER_PROVIDER

        # All providers down
        logger.error("All providers unavailable")
        raise Exception("No available providers")

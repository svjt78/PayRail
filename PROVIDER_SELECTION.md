# Provider Selection Rules

This document explains how PayRail decides which provider (`providerA`, `providerB`) is used when a payment is **authorized**.

## Decision Order (Highest Priority → Lowest)

1. **Preferred Provider (if provided in the request)**
   - If a request explicitly asks for a provider and that provider’s circuit breaker allows execution, it is chosen.

2. **Country-Based Routing**
   - If a country is provided and matches a routing rule, the mapped provider is chosen (if available).
   - Current rules:
     - `DE`, `FR`, `GB`, `JP` → `providerB`
     - `US`, `CA`, `AU` → `providerA`

3. **Amount-Based Routing**
   - If the payment amount is **>= $100 (10,000 cents)**, route to `providerB` (if available).

4. **Default Provider**
   - If no rule matches (or previous choices are unavailable), use the default provider:
     - `DEFAULT_PROVIDER=providerA`

5. **Failover Provider**
   - If the default provider’s circuit is **OPEN**, fail over to:
     - `FAILOVER_PROVIDER=providerB`

If **all providers are unavailable**, the authorization fails with an error.

## Circuit Breaker Interaction

Each provider has a file-backed circuit breaker:
- If the circuit is **OPEN**, the provider is considered unavailable.
- Once the recovery timeout expires, it may allow limited calls in **HALF_OPEN**.

The routing engine only selects providers whose circuit breaker **can execute**.

## Where This Is Implemented

- `backend/api_gateway/services/routing.py`
- Circuit breaker: `backend/api_gateway/services/circuit_breaker.py`

## How to Configure

These values live in the root `.env`:

```
DEFAULT_PROVIDER=providerA
FAILOVER_PROVIDER=providerB
CB_FAILURE_THRESHOLD=5
CB_RECOVERY_TIMEOUT=30
CB_HALF_OPEN_MAX_CALLS=3
```

You can also inject provider failures from the UI (`/providers`) to test routing and failover behavior.

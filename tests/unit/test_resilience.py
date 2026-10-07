import asyncio

import pytest

from support_dispatcher.core.config import CircuitBreakerOpenError
from support_dispatcher.resilience.circuit_breaker import CircuitBreaker, CircuitState


@pytest.mark.asyncio
async def test_circuit_breaker_tripping_and_recovery():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

    async def fail_call():
        raise RuntimeError("Service failure")

    async def success_call():
        return "success"

    # 1. Successful calls
    res = await cb.call(success_call)
    assert res == "success"
    assert cb.state == CircuitState.CLOSED

    # 2. Trigger failures up to threshold
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await cb.call(fail_call)

    assert cb.state == CircuitState.OPEN

    # 3. Call while OPEN should immediately raise CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(success_call)

    # 4. Wait for recovery timeout -> HALF_OPEN
    await asyncio.sleep(0.15)
    res_recovered = await cb.call(success_call)
    assert res_recovered == "success"
    assert cb.state == CircuitState.CLOSED

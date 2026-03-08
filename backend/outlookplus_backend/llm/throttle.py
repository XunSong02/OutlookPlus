from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, TypeVar


T = TypeVar("T")


@dataclass
class RateLimiter:
    min_interval_seconds: float = 0.0

    _next_allowed: float = 0.0

    def wait(self) -> None:
        if self.min_interval_seconds <= 0:
            return
        now = time.time()
        if now < self._next_allowed:
            time.sleep(self._next_allowed - now)
        self._next_allowed = time.time() + self.min_interval_seconds


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 4.0

    def run(self, fn: Callable[[], T], *, is_retryable: Callable[[Exception], bool]) -> T:
        attempt = 0
        while True:
            attempt += 1
            try:
                return fn()
            except Exception as e:
                if attempt >= self.max_attempts or not is_retryable(e):
                    raise
                delay = min(self.max_delay_seconds, self.base_delay_seconds * (2 ** (attempt - 1)))
                delay = delay * (0.8 + 0.4 * random.random())
                time.sleep(delay)

from collections import deque
from typing import Any, Optional, Tuple


class RingBuffer:
    """Time-ordered (timestamp, value) samples, pruned to a rolling max age."""

    def __init__(self, max_age_seconds: float):
        self.max_age_seconds = max_age_seconds
        self._samples: deque = deque()

    def append(self, timestamp: float, value: Any) -> None:
        self._samples.append((timestamp, value))
        self._prune(timestamp)

    def _prune(self, now: float) -> None:
        cutoff = now - self.max_age_seconds
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    def value_at_or_before(self, timestamp: float, default: Any = None) -> Any:
        result = default
        for ts, value in self._samples:
            if ts <= timestamp:
                result = value
            else:
                break
        return result

    def oldest(self) -> Optional[Tuple[float, Any]]:
        return self._samples[0] if self._samples else None

    def newest(self) -> Optional[Tuple[float, Any]]:
        return self._samples[-1] if self._samples else None

    def clear(self) -> None:
        self._samples.clear()

    def __len__(self) -> int:
        return len(self._samples)

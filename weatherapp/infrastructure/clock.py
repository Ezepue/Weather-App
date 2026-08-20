"""Time as a dependency.

Every "now" in the system comes from here, so tests can freeze it instead of
tolerating a moving target.
"""

from __future__ import annotations

from datetime import datetime, timezone


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def epoch(self) -> int:
        return int(self.now().timestamp())


class FrozenClock:
    def __init__(self, moment: datetime):
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        self._moment = moment

    def now(self) -> datetime:
        return self._moment

    def epoch(self) -> int:
        return int(self._moment.timestamp())

    def advance(self, seconds: float) -> None:
        from datetime import timedelta
        self._moment = self._moment + timedelta(seconds=seconds)

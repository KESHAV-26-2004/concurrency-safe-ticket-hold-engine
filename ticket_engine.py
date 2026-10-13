
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Callable
from uuid import uuid4


class HoldError(Exception):
    pass


class SeatUnavailable(HoldError):
    pass


class HoldNotFound(HoldError):
    pass


class InvalidRequest(HoldError):
    pass


class SeatLimitExceeded(HoldError):
    pass


class SeatState(str, Enum):
    FREE = "FREE"
    HELD = "HELD"
    SOLD = "SOLD"


@dataclass
class Hold:
    hold_id: str
    seat_id: str
    user_id: str
    created_at: float
    expires_at: float
    state: str = "active"


@dataclass(frozen=True)
class SeatStatus:
    state: SeatState
    user_id: str | None = None
    expires_at: float | None = None


class TicketHoldEngine:
    def __init__(
        self,
        clock: Callable[[], float],
        max_holds_per_user: int = 4,
    ):
        if max_holds_per_user < 1:
            raise ValueError("max_holds_per_user must be positive")

        self._clock = clock
        self._max_holds_per_user = max_holds_per_user
        self._lock = RLock()
        self._holds = {}
        self._seat_holds = {}
        self._sold = {}
        self._seat_last_hold = {}

    def _now(self) -> float:
        return float(self._clock())

    def _expire_current_hold(self, seat_id: str, now: float) -> None:
        hold_id = self._seat_holds.get(seat_id)
        if hold_id is None:
            return

        hold = self._holds[hold_id]
        if hold.expires_at <= now:
            hold.state = "expired"
            del self._seat_holds[seat_id]

    def _expire_all(self, now: float) -> None:
        for seat_id in list(self._seat_holds):
            self._expire_current_hold(seat_id, now)

    def _active_count(self, user_id: str, now: float) -> int:
        self._expire_all(now)
        return sum(
            1
            for hold_id in self._seat_holds.values()
            if self._holds[hold_id].user_id == user_id
        )

    def hold(self, seat_id: str, user_id: str, ttl_seconds: float) -> str:
        if not seat_id or not user_id:
            raise InvalidRequest("seat_id and user_id are required")
        if ttl_seconds <= 0:
            raise InvalidRequest("ttl_seconds must be greater than zero")

        with self._lock:
            now = self._now()
            self._expire_current_hold(seat_id, now)

            if seat_id in self._sold:
                raise SeatUnavailable(f"{seat_id} is already sold")

            current_id = self._seat_holds.get(seat_id)
            if current_id is not None:
                current = self._holds[current_id]
                if current.user_id == user_id:
                    return current.hold_id
                raise SeatUnavailable(f"{seat_id} is already held")

            if self._active_count(user_id, now) >= self._max_holds_per_user:
                raise SeatLimitExceeded("user has reached the seat limit")

            hold_id = str(uuid4())
            hold = Hold(
                hold_id=hold_id,
                seat_id=seat_id,
                user_id=user_id,
                created_at=now,
                expires_at=now + float(ttl_seconds),
            )

            self._holds[hold_id] = hold
            self._seat_holds[seat_id] = hold_id
            self._seat_last_hold[seat_id] = hold_id

            return hold_id

    def seat_status(self, seat_id: str) -> SeatStatus:
        with self._lock:
            now = self._now()
            self._expire_current_hold(seat_id, now)

            if seat_id in self._sold:
                return SeatStatus(SeatState.SOLD, self._sold[seat_id])

            hold_id = self._seat_holds.get(seat_id)
            if hold_id is None:
                return SeatStatus(SeatState.FREE)

            hold = self._holds[hold_id]
            return SeatStatus(
                SeatState.HELD,
                hold.user_id,
                hold.expires_at,
            )

    def get_hold(self, hold_id: str) -> Hold:
        with self._lock:
            hold = self._holds.get(hold_id)
            if hold is None:
                raise HoldNotFound(hold_id)

            return Hold(**vars(hold))

    
    def confirm(self, hold_id: str) -> None:
        with self._lock:
            now = self._now()
            hold = self._holds.get(hold_id)

            if hold is None:
                raise HoldNotFound(hold_id)

            if hold.state == "confirmed":
                return

            if hold.state in {"released", "superseded"}:
                raise HoldNotFound("hold is no longer confirmable")

            if hold.seat_id in self._sold:
                raise SeatUnavailable("seat is already sold")

            current_id = self._seat_holds.get(hold.seat_id)

            if current_id == hold_id:
                if hold.expires_at <= now:
                    self._expire_current_hold(hold.seat_id, now)
                    current_id = self._seat_holds.get(hold.seat_id)
            elif current_id is not None:
                raise SeatUnavailable("seat has been reassigned")

            if current_id is None:
                last_id = self._seat_last_hold.get(hold.seat_id)

                if last_id != hold_id:
                    raise SeatUnavailable("seat has been reassigned")

                if hold.state == "active":
                    hold.state = "expired"

            self._sold[hold.seat_id] = hold.user_id
            self._seat_holds.pop(hold.seat_id, None)
            hold.state = "confirmed"

    def release(self, hold_id: str) -> None:
        with self._lock:
            hold = self._holds.get(hold_id)

            if hold is None:
                raise HoldNotFound(hold_id)

            if hold.state == "confirmed":
                raise SeatUnavailable("a sold seat cannot be released")

            if hold.state in {"released", "expired", "superseded"}:
                return

            if self._seat_holds.get(hold.seat_id) == hold_id:
                del self._seat_holds[hold.seat_id]

            hold.state = "released"
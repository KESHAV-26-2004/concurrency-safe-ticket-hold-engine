
import unittest

from ticket_engine import (
    InvalidRequest,
    SeatLimitExceeded,
    SeatState,
    SeatUnavailable,
    TicketHoldEngine,
)


class FakeClock:
    def __init__(self, start=100.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TicketEngineTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.engine = TicketHoldEngine(clock=self.clock)

    def test_hold_and_retry(self):
        first = self.engine.hold("A1", "user-1", 10)
        second = self.engine.hold("A1", "user-1", 50)

        self.assertEqual(first, second)
        self.assertEqual(
            self.engine.get_hold(first).expires_at,
            110.0,
        )

    def test_expiry_frees_seat(self):
        self.engine.hold("A1", "user-1", 5)
        self.clock.advance(6)

        self.assertEqual(
            self.engine.seat_status("A1").state,
            SeatState.FREE,
        )

    def test_confirmed_seat_cannot_be_held_again(self):
        hold_id = self.engine.hold("A1", "user-1", 30)
        self.engine.confirm(hold_id)

        with self.assertRaises(SeatUnavailable):
            self.engine.hold("A1", "user-2", 30)

    def test_expired_hold_cannot_confirm_after_reassignment(self):
        old_hold = self.engine.hold("A1", "user-1", 5)
        self.clock.advance(6)
        new_hold = self.engine.hold("A1", "user-2", 30)

        with self.assertRaises(SeatUnavailable):
            self.engine.confirm(old_hold)

        self.engine.confirm(new_hold)
        self.assertEqual(
            self.engine.seat_status("A1").user_id,
            "user-2",
        )

    def test_release_frees_held_seat(self):
        hold_id = self.engine.hold("A1", "user-1", 30)
        self.engine.release(hold_id)

        self.assertEqual(
            self.engine.seat_status("A1").state,
            SeatState.FREE,
        )

    def test_four_seat_limit(self):
        for seat in ("A1", "A2", "A3", "A4"):
            self.engine.hold(seat, "user-1", 30)

        with self.assertRaises(SeatLimitExceeded):
            self.engine.hold("A5", "user-1", 30)

    def test_bulk_failure_does_not_reserve_any_new_seat(self):
        self.engine.hold("A2", "user-2", 30)

        with self.assertRaises(SeatUnavailable):
            self.engine.hold_many(
                "user-1",
                ["A1", "A2", "A3"],
                30,
            )

        self.assertEqual(
            self.engine.seat_status("A1").state,
            SeatState.FREE,
        )
        self.assertEqual(
            self.engine.seat_status("A3").state,
            SeatState.FREE,
        )

    def test_bulk_request_respects_seat_limit(self):
        for seat in ("B1", "B2", "B3"):
            self.engine.hold(seat, "user-1", 30)

        with self.assertRaises(SeatLimitExceeded):
            self.engine.hold_many(
                "user-1",
                ["B4", "B5"],
                30,
            )

        self.assertEqual(
            self.engine.seat_status("B4").state,
            SeatState.FREE,
        )
        self.assertEqual(
            self.engine.seat_status("B5").state,
            SeatState.FREE,
        )


if __name__ == "__main__":
    unittest.main()

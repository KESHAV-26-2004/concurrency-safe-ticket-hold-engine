
import random
import unittest

from test_concurrency import FakeClock
from ticket_engine import HoldError, SeatState, TicketHoldEngine


class ModelBasedTests(unittest.TestCase):
    def test_randomized_hold_and_expiry_sequences(self):
        rng = random.Random(20261013)
        clock = FakeClock()
        engine = TicketHoldEngine(clock)

        seats = ["A", "B", "C"]
        users = ["alice", "bob"]
        model = {seat: {"state": "FREE", "user": None, "expires": None}
                 for seat in seats}

        for step in range(300):
            seat = rng.choice(seats)
            user = rng.choice(users)
            operation = rng.choice(["hold", "status", "advance"])

            if operation == "advance":
                clock.advance(rng.randint(1, 3))
                for item in model.values():
                    if item["state"] == "HELD" and item["expires"] <= clock():
                        item.update(state="FREE", user=None, expires=None)

            elif operation == "hold":
                ttl = rng.randint(1, 5)
                expected_ok = model[seat]["state"] == "FREE"
                if model[seat]["state"] == "HELD":
                    expected_ok = model[seat]["user"] == user

                try:
                    hold_id = engine.hold(seat, user, ttl)
                    self.assertTrue(expected_ok, f"Unexpected hold success at step {step}")
                    if model[seat]["state"] == "FREE":
                        model[seat] = {
                            "state": "HELD",
                            "user": user,
                            "expires": clock() + ttl,
                        }
                except HoldError:
                    self.assertFalse(expected_ok, f"Unexpected hold failure at step {step}")

            else:
                status = engine.seat_status(seat)
                expected = model[seat]

                if expected["state"] == "HELD" and expected["expires"] <= clock():
                    expected.update(state="FREE", user=None, expires=None)

                self.assertEqual(status.state.value, expected["state"], f"Seat state mismatch at step {step}")

                if expected["state"] == "HELD":
                    self.assertEqual(status.user_id, expected["user"])
                    self.assertEqual(status.expires_at, expected["expires"])
                elif expected["state"] == "FREE":
                    self.assertIsNone(status.user_id)

        print("Model-based randomized test passed")


if __name__ == "__main__":
    unittest.main()

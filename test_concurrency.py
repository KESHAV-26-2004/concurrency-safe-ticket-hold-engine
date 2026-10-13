
import random
import threading
import unittest

from ticket_engine import HoldError, SeatState, TicketHoldEngine


class FakeClock:
    def __init__(self, start=100.0):
        self._time = start
        self._lock = threading.Lock()

    def __call__(self):
        with self._lock:
            return self._time

    def advance(self, seconds):
        with self._lock:
            self._time += seconds


class ConcurrencyTests(unittest.TestCase):
    def test_random_operations_preserve_invariants(self):
        seed = 913704
        print(f"Random seed: {seed}")

        clock = FakeClock()
        engine = TicketHoldEngine(clock)
        users = [f"user-{i}" for i in range(8)]
        seats = [f"seat-{i}" for i in range(6)]

        known_holds = set()
        confirmed_holds = set()
        holds_lock = threading.Lock()
        confirmed_lock = threading.Lock()
        errors = []

        def worker(worker_seed):
            local_rng = random.Random(worker_seed)

            for _ in range(250):
                operation = local_rng.choice(
                    ["hold", "confirm", "release", "many", "status"]
                )
                user_id = local_rng.choice(users)
                seat_id = local_rng.choice(seats)

                try:
                    if operation == "hold":
                        hold_id = engine.hold(
                            seat_id, user_id, local_rng.randint(1, 20)
                        )
                        with holds_lock:
                            known_holds.add(hold_id)

                    elif operation == "many":
                        requested = local_rng.sample(
                            seats, local_rng.randint(1, 3)
                        )
                        hold_ids = engine.hold_many(
                            user_id, requested, local_rng.randint(1, 20)
                        )
                        with holds_lock:
                            known_holds.update(hold_ids)

                    elif operation in ("confirm", "release"):
                        with holds_lock:
                            hold_id = (
                                local_rng.choice(tuple(known_holds))
                                if known_holds else None
                            )

                        if hold_id is not None:
                            if operation == "confirm":
                                before = engine.get_hold(hold_id)
                                engine.confirm(hold_id)
                                after = engine.get_hold(hold_id)

                                if (
                                    before.state != "confirmed"
                                    and after.state == "confirmed"
                                ):
                                    with confirmed_lock:
                                        confirmed_holds.add(hold_id)
                            else:
                                engine.release(hold_id)

                    else:
                        engine.seat_status(seat_id)

                    if local_rng.random() < 0.05:
                        clock.advance(1)

                except HoldError:
                    pass
                except Exception as exc:
                    errors.append(repr(exc))

        threads = [
            threading.Thread(target=worker, args=(seed + i + 1,))
            for i in range(12)
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])

        confirmed_by_seat = {}
        active_by_user = {}

        for hold_id in known_holds:
            hold = engine.get_hold(hold_id)

            if hold.state == "confirmed":
                confirmed_by_seat.setdefault(hold.seat_id, set()).add(hold_id)

            if hold.state == "active" and hold.expires_at > clock():
                active_by_user[hold.user_id] = (
                    active_by_user.get(hold.user_id, 0) + 1
                )

        for seat_id, hold_ids in confirmed_by_seat.items():
            self.assertEqual(
                len(hold_ids), 1,
                f"Seat {seat_id} has multiple confirmed holds",
            )

        self.assertTrue(
            all(count <= 4 for count in active_by_user.values()),
            f"User exceeded hold limit: {active_by_user}",
        )

        for seat_id in seats:
            status = engine.seat_status(seat_id)
            if status.state == SeatState.SOLD:
                self.assertIsNotNone(status.user_id)

        print("Concurrency stress test passed")


if __name__ == "__main__":
    unittest.main()

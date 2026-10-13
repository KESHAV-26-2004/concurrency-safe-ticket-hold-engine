
from ticket_engine import (
    SeatLimitExceeded,
    SeatState,
    SeatUnavailable,
    TicketHoldEngine,
)


def test_confirmation_and_release():
    now = [100.0]
    engine = TicketHoldEngine(clock=lambda: now[0])

    hold_id = engine.hold("A1", "user-1", 10)
    engine.confirm(hold_id)

    assert engine.seat_status("A1").state == SeatState.SOLD

    try:
        engine.hold("A1", "user-2", 10)
        raise AssertionError("A sold seat must not be held again")
    except SeatUnavailable:
        pass

    engine = TicketHoldEngine(clock=lambda: now[0])
    old_hold = engine.hold("A2", "user-1", 5)

    now[0] = 106.0
    new_hold = engine.hold("A2", "user-2", 20)

    try:
        engine.confirm(old_hold)
        raise AssertionError("A superseded hold must not be confirmed")
    except SeatUnavailable:
        pass

    engine.confirm(new_hold)
    assert engine.seat_status("A2").user_id == "user-2"

    engine = TicketHoldEngine(clock=lambda: now[0])
    hold_id = engine.hold("A3", "user-1", 20)
    engine.release(hold_id)

    assert engine.seat_status("A3").state == SeatState.FREE

    print("Confirmation and release checks passed")


def test_bulk_holds():
    now = [100.0]
    engine = TicketHoldEngine(clock=lambda: now[0])

    engine.hold("A2", "user-2", 30)

    try:
        engine.hold_many("user-1", ["A1", "A2", "A3"], 30)
        raise AssertionError("Bulk hold should fail")
    except SeatUnavailable:
        pass

    assert engine.seat_status("A1").state == SeatState.FREE
    assert engine.seat_status("A3").state == SeatState.FREE

    engine.hold_many("user-1", ["B1", "B2", "B3"], 30)

    try:
        engine.hold_many("user-1", ["B4", "B5"], 30)
        raise AssertionError("Four-seat limit should be enforced")
    except SeatLimitExceeded:
        pass

    assert engine.seat_status("B4").state == SeatState.FREE
    assert engine.seat_status("B5").state == SeatState.FREE

    print("Bulk hold checks passed")


if __name__ == "__main__":
    test_confirmation_and_release()
    test_bulk_holds()

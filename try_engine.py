
from ticket_engine import SeatState, SeatUnavailable, TicketHoldEngine


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

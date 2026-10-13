
# Bugs I Fear

1. **Concurrent confirmation:** Two threads might try to confirm different holds for the same seat. Confirmation must remain atomic so the seat is sold only once.

2. **Expired hold after reassignment:** An old hold must not confirm after another user has taken the seat.

3. **Hold limit race:** Concurrent requests must not allow a user to exceed the maximum of four active holds.

4. **Partial bulk reservation:** If any requested seat is unavailable or the user exceeds the limit, a bulk request must not reserve only part of the requested seats.

5. **Retry extending expiry:** Retrying the same hold must return the existing ID without extending its expiry.

6. **Release affecting a newer hold:** Releasing an old hold must not remove a newer user's reservation for the same seat.

7. **Clock boundary:** A hold expires when its expiry time is less than or equal to the current time.

8. **In-memory persistence:** Restarting the process loses all reservations. A production implementation would need durable storage and transactional coordination.

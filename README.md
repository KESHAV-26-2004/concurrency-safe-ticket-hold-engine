
# Concurrency-Safe Ticket Hold Engine

A small in-memory ticket reservation engine built in Python. It supports temporary seat holds, confirmation, release, expiry, idempotent retries, bulk holds, and concurrent requests.

## Features

- Hold a seat for a user for a fixed duration.
- Return the same hold ID when the same user retries an existing hold.
- Confirm a hold and mark its seat as sold.
- Release an active hold.
- Check whether a seat is free, held, or sold.
- Enforce a maximum of four active holds per user.
- Support all-or-nothing bulk holds.
- Use an injectable clock for deterministic expiry tests.
- Protect state changes with a lock.

## Project files

- `ticket_engine.py` — core implementation.
- `test_ticket_engine.py` — functional tests.
- `test_concurrency.py` — multithreaded stress test.
- `test_model_based.py` — randomized comparison against a simple reference model.
- `DECISIONS.md` — behavior choices and trade-offs.
- `AI_USAGE.md` — disclosure of AI assistance.
- `BUGS_I_FEAR.md` — risks and limitations.

## Run the tests

Use Python 3.12 or a compatible Python version.

```bash
python -m unittest -v
```

## Concurrency approach

A single reentrant lock protects operations that read and modify shared state. This keeps seat allocation and confirmation atomic and avoids complicated lock ordering.

## Expiry behavior

The clock is injected into the engine, allowing tests to advance time without sleeping. Expired holds are cleaned up when relevant operations occur.

## Limitations

This implementation stores state in memory, so data is lost when the process stops. It is intended as an assignment demonstrating concurrency and state management, not as a production ticketing service.

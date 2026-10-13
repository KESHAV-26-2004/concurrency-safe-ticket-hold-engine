# Decisions I made before coding

The brief is intentionally a little messy. I don't think every rule can be followed literally in every situation, so I want to be clear about the behavior I'm choosing instead of hiding those cases in the implementation.

## Expiry and confirmation

An expired hold should not automatically become useless if nobody has taken the seat since it expired. I'll keep enough information about a hold to tell whether its seat has been reassigned. If another hold has taken the seat, or the seat has been sold, the old hold cannot be confirmed.

For a seat that is still free, I will allow its original expired hold to be confirmed only while it has not been assigned to someone else. Confirmation must still be atomic with checking the seat's ownership.

## Retrying the same hold

A repeat request from the same user for a seat they currently hold should return the same hold ID. It must not create another hold or move the expiry time.

If that hold has expired, the retry follows the normal availability rules. It must not bring an old hold back to life after the seat has been reassigned.

## The four-seat limit

The limit applies to a user's current, unexpired holds. Expired and released holds no longer count. A sold seat is no longer a hold.

I'll check the limit while holding the same lock used for seat changes. Otherwise, two requests could both see three holds and each add another seat.

## Bulk requests

`hold_many` should either reserve all requested seats or reserve none of them. I'll check for duplicate seat IDs and reject them rather than guessing what a duplicate means. I'll also validate seat availability and the four-seat limit before making any changes.

A repeated request for a seat the user already holds is treated as an idempotent retry; it does not create a second hold. The batch still has to fit the four-seat limit and satisfy the availability checks for any new seats.

## Expiry and time

The clock will be passed into the engine, so tests can move time forward without sleeping. Expiry will be checked when an operation needs to know the current state. A hold's original expiry time is fixed and never extended.

## Locking

I'll start with one lock around the shared state. This is less clever than locking each seat separately, but it makes the correctness argument much easier: validation and state changes happen together. It also avoids deadlocks when two bulk requests contain the same seats in different orders.

If this were a high-throughput production service, I would measure contention before choosing a more complicated locking design.

## Release

Releasing a hold should only free a seat if that hold still owns it. An old or superseded hold must never clear a newer user's reservation. Releasing a sold seat does not undo the sale.

## Errors

Invalid input, an unavailable seat, an invalid TTL, a duplicate seat in a bulk request, or a seat-limit violation should fail clearly. The caller should not have to infer a failure from a partial state change.

## What I still need to verify

These choices are my interpretation of the brief, not the only possible interpretation. The tests should make the chosen behavior explicit, especially around expiry, retrying an expired hold, and bulk requests that include seats already held by the same user.

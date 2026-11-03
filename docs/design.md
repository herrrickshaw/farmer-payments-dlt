# Design

## Principle

Use DLT where several parties who don't fully trust each other need one shared, tamper-evident
record (buyer, FPO, bank, agency, arbiter). Do not use it where a single database would do —
CGAP's guidance is that conventional approaches often win on cost and complexity.

## Actors and nodes (consortium)

FPO / FPO federation · Procurer or mandi buyer · Partner bank · Government agency · Arbiter
(e.g. mandi board). Farmers are *beneficiaries*, identified by registry ID; they do not hold keys.

## Flows

1. **Procurement escrow**: buyer funds → `FUNDED` → delivery confirmed at ≥ promised grade →
   `RELEASED` (bank instructed) or `DISPUTED` → arbiter sets farmer share → `SETTLED`.
2. **Scheme disbursement**: agency submits (scheme, period, farmer ID, verified flag). The ledger
   rejects duplicates and unverified IDs; the bank pays via DBT/UPI.
3. **Reconciliation**: compare ledger-approved amounts with bank credits; surface shortfalls.

## On-ledger vs off-ledger

| On-ledger | Off-ledger |
|---|---|
| Escrow state transitions, approvals, hashes of weighment slips / grade certificates | Money (bank/UPI), KYC data, documents, photos |

## Open design questions

- Who funds an escrow if buyers pay on credit? (Needs bank-guarantee integration.)
- Grade disputes need an objective oracle (lab/assaying); the prototype just trusts the buyer's entry.
- Real signatures (asymmetric keys, HSM) and key recovery governance.
- Platform choice: Fabric (permissioned, mature) vs EVM L2 (more tooling, public data exposure).

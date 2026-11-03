# farmer-payments-dlt

Distributed-ledger (DLT) applications for **farmer payments**: a literature base, a catalogue of
open-source repos, a design note, and a small runnable prototype.

Seeded by Deshmukh & Patil (2022), *Applications and Challenges of Blockchain Technology in
Agriculture Sector: A Review*, J. Agricultural Extension Management 23(1), 159–176 — see
[docs/article-notes.md](docs/article-notes.md).

## Contents

| Path | What |
|---|---|
| [docs/article-notes.md](docs/article-notes.md) | What the article says, mapped to payment use cases and its listed challenges |
| [docs/literature.md](docs/literature.md) | Papers, reports and pilots (with verification status) |
| [docs/related-repos.md](docs/related-repos.md) | GitHub repos found, with stars/last-push/licence and what each is useful for |
| [docs/design.md](docs/design.md) | Payment flows, who runs the nodes, what stays off-chain |
| `src/fpdlt/ledger.py` | Stdlib-only prototype: hash-chained consortium ledger, procurement escrow, scheme disbursement, reconciliation |
| `tests/` | Unit tests (`python3 -m unittest discover -s tests`) |

## Use cases covered by the prototype

1. **Procurement escrow** (buyer/FPO → farmer): funds committed up front, released on confirmed
   delivery at the promised grade, otherwise held for arbitration.
2. **Scheme disbursement** (agency → farmer): one payment per (scheme, period, farmer); unverified
   IDs rejected.
3. **Reconciliation**: ledger-approved payments vs. credits actually seen on the bank/UPI rail.

## Honest scope

- The ledger records instructions and confirmations; money moves on existing rails.
- Prototype only: HMAC "signatures", no networking or consensus. Production would use a permissioned
  platform (e.g. Hyperledger Fabric) or an EVM chain with audited contracts.
- Many sources here are hackathon-grade repos and vendor/pilot reports; read the verification
  column before relying on any claim.

## Run

```bash
python3 -m unittest discover -s tests -v
```

MIT licensed.

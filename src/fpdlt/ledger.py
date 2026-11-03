"""Minimal permissioned, hash-chained ledger for farmer payments.

This is a teaching/prototype ledger, not a production DLT. It models the three
properties the reviewed article stresses (tamper-evidence, a permissioned
consortium, smart-contract-style rules) with the standard library only.

The ledger records payment *instructions and confirmations*. Money itself moves
on existing rails (UPI/NEFT/DBT); the ledger is the shared, auditable record.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field

GENESIS = "0" * 64


class LedgerError(Exception):
    pass


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


@dataclass
class Ledger:
    """Consortium ledger: only registered members (with a key) may append."""

    members: dict[str, bytes] = field(default_factory=dict)  # org id -> secret
    blocks: list[dict] = field(default_factory=list)
    escrows: dict[str, dict] = field(default_factory=dict)
    disbursed: set[tuple[str, str, str]] = field(default_factory=set)

    # -- membership / chain -------------------------------------------------
    def register(self, org: str, secret: bytes) -> None:
        self.members[org] = secret

    def _sign(self, org: str, payload: dict) -> str:
        return hmac.new(self.members[org], json.dumps(payload, sort_keys=True).encode(),
                        hashlib.sha256).hexdigest()

    def append(self, org: str, kind: str, data: dict) -> dict:
        if org not in self.members:
            raise LedgerError(f"{org} is not a consortium member")
        payload = {"kind": kind, "data": data, "by": org}
        block = {
            "index": len(self.blocks),
            "ts": time.time(),
            "prev": self.blocks[-1]["hash"] if self.blocks else GENESIS,
            "payload": payload,
            "sig": self._sign(org, payload),
        }
        block["hash"] = _h({k: block[k] for k in ("index", "ts", "prev", "payload", "sig")})
        self.blocks.append(block)
        return block

    def verify(self) -> bool:
        prev = GENESIS
        for i, b in enumerate(self.blocks):
            body = {k: b[k] for k in ("index", "ts", "prev", "payload", "sig")}
            if b["index"] != i or b["prev"] != prev or b["hash"] != _h(body):
                return False
            org = b["payload"]["by"]
            if org not in self.members or not hmac.compare_digest(
                    b["sig"], self._sign(org, b["payload"])):
                return False
            prev = b["hash"]
        return True

    # -- contract 1: procurement escrow (buyer/FPO -> farmer) ----------------
    def open_escrow(self, buyer: str, escrow_id: str, farmer_id: str, amount: float,
                    min_grade: str) -> None:
        if escrow_id in self.escrows:
            raise LedgerError("duplicate escrow id")
        if amount <= 0:
            raise LedgerError("amount must be positive")
        self.escrows[escrow_id] = dict(buyer=buyer, farmer=farmer_id, amount=amount,
                                       min_grade=min_grade, state="FUNDED")
        self.append(buyer, "escrow_funded", dict(id=escrow_id, farmer=farmer_id,
                                                 amount=amount, min_grade=min_grade))

    def confirm_delivery(self, buyer: str, escrow_id: str, grade: str, qty_kg: float) -> str:
        """Release if delivered grade >= promised grade, else hold for dispute."""
        e = self._escrow(escrow_id, "FUNDED")
        if buyer != e["buyer"]:
            raise LedgerError("only the funding buyer can confirm delivery")
        ok = grade <= e["min_grade"]  # grades 'A' < 'B' < 'C': A is best
        e["state"] = "RELEASED" if ok else "DISPUTED"
        self.append(buyer, "escrow_" + e["state"].lower(),
                    dict(id=escrow_id, grade=grade, qty_kg=qty_kg))
        return e["state"]

    def resolve_dispute(self, arbiter: str, escrow_id: str, pay_farmer_pct: float) -> None:
        e = self._escrow(escrow_id, "DISPUTED")
        if not 0 <= pay_farmer_pct <= 100:
            raise LedgerError("pct out of range")
        e["state"] = "SETTLED"
        self.append(arbiter, "escrow_settled", dict(id=escrow_id, farmer_pct=pay_farmer_pct))

    def _escrow(self, escrow_id: str, state: str) -> dict:
        e = self.escrows.get(escrow_id)
        if not e:
            raise LedgerError("unknown escrow")
        if e["state"] != state:
            raise LedgerError(f"escrow is {e['state']}, expected {state}")
        return e

    # -- contract 2: scheme disbursement (government -> farmer) --------------
    def disburse(self, agency: str, scheme: str, period: str, farmer_id: str,
                 amount: float, verified: bool) -> None:
        """One payment per (scheme, period, farmer); blocks duplicates and unverified IDs."""
        key = (scheme, period, farmer_id)
        if not verified:
            raise LedgerError("farmer identity not verified")
        if key in self.disbursed:
            raise LedgerError("duplicate disbursement")
        self.disbursed.add(key)
        self.append(agency, "dbt_disbursed", dict(scheme=scheme, period=period,
                                                  farmer=farmer_id, amount=amount))

    # -- reconciliation against the off-chain bank/UPI rail -----------------
    def reconcile(self, bank_credits: dict[str, float]) -> dict[str, float]:
        """Return farmer -> shortfall for ledger-approved payments the bank has not credited."""
        owed: dict[str, float] = {}
        for b in self.blocks:
            k, d = b["payload"]["kind"], b["payload"]["data"]
            if k == "escrow_released":
                e = self.escrows[d["id"]]
                owed[e["farmer"]] = owed.get(e["farmer"], 0) + e["amount"]
            elif k == "dbt_disbursed":
                owed[d["farmer"]] = owed.get(d["farmer"], 0) + d["amount"]
        return {f: round(a - bank_credits.get(f, 0), 2) for f, a in owed.items()
                if a - bank_credits.get(f, 0) > 0}

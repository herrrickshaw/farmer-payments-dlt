"""In-memory behaviour tests for fpdlt.ledger (pure stdlib ledger; no network, no payment rail, no real money)."""
import hashlib
import hmac
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import fpdlt  # noqa: E402
from fpdlt import ledger as ledger_mod  # noqa: E402
from fpdlt.ledger import GENESIS, Ledger, LedgerError, _h  # noqa: E402


@pytest.fixture()
def L(monkeypatch):
    ticks = iter(range(1000, 100000))
    monkeypatch.setattr(ledger_mod.time, "time", lambda: float(next(ticks)))
    led = Ledger()
    for org in ("FPO-1", "AgriBank", "Agency", "Arbiter"):
        led.register(org, org.encode() + b"-secret")
    return led


def test_package_exports():
    assert fpdlt.Ledger is Ledger and fpdlt.LedgerError is LedgerError
    assert set(fpdlt.__all__) == {"Ledger", "LedgerError"}
    assert GENESIS == "0" * 64 and issubclass(LedgerError, Exception)


def test_hash_helper_is_key_order_independent_and_sha256():
    assert _h({"a": 1, "b": 2}) == _h({"b": 2, "a": 1})
    assert _h({"a": 1}) == hashlib.sha256(b'{"a": 1}').hexdigest()
    assert _h({"a": 1}) != _h({"a": 2}) and len(_h([])) == 64


def test_empty_ledger_verifies_and_defaults_are_not_shared():
    a, b = Ledger(), Ledger()
    assert a.verify() is True
    a.register("x", b"k")
    assert b.members == {} and a.members == {"x": b"k"}
    a.disbursed.add(("s", "p", "f"))
    assert b.disbursed == set() and b.blocks == [] and b.escrows == {}


def test_append_links_blocks_and_signs_with_the_orgs_key(L):
    b0 = L.append("FPO-1", "note", {"n": 1})
    b1 = L.append("Agency", "note", {"n": 2})
    assert (b0["index"], b1["index"]) == (0, 1)
    assert b0["prev"] == GENESIS and b1["prev"] == b0["hash"]
    assert b0["ts"] == 1000.0 and b1["ts"] == 1001.0
    assert b0["payload"] == {"kind": "note", "data": {"n": 1}, "by": "FPO-1"}
    want = hmac.new(b"FPO-1-secret", json.dumps(b0["payload"], sort_keys=True).encode(), hashlib.sha256).hexdigest()
    assert b0["sig"] == want
    assert b0["hash"] == _h({k: b0[k] for k in ("index", "ts", "prev", "payload", "sig")})
    assert L.blocks == [b0, b1] and L.verify()


def test_append_rejects_non_member_without_writing(L):
    with pytest.raises(LedgerError, match="Mallory is not a consortium member"):
        L.append("Mallory", "x", {})
    assert L.blocks == []


@pytest.mark.parametrize("mutate", [
    lambda L: L.blocks[1].__setitem__("prev", GENESIS),                       # broken link
    lambda L: L.blocks[1].__setitem__("index", 5),                             # wrong index
    lambda L: L.blocks[0].__setitem__("ts", 1.0),                              # timestamp edit
    lambda L: L.blocks[0].__setitem__("hash", "0" * 64),                       # hash overwrite
    lambda L: L.blocks[0]["payload"]["data"].__setitem__("n", 99),             # payload edit
    lambda L: L.blocks[0].__setitem__("sig", "f" * 64),                        # bad signature
    lambda L: L.members.pop("FPO-1"),                                          # author left the consortium
    lambda L: L.members.__setitem__("FPO-1", b"other"),                        # key rotated
    lambda L: L.blocks.pop(0),                                                 # head removed
    lambda L: L.blocks.reverse(),                                              # reorder
])
def test_verify_detects_each_kind_of_tampering(L, mutate):
    L.append("FPO-1", "note", {"n": 1})
    L.append("Agency", "note", {"n": 2})
    assert L.verify()
    mutate(L)
    assert L.verify() is False


def test_verify_rehashed_forgery_still_fails_on_signature(L):
    """An attacker who edits a payload AND recomputes the hash still cannot forge the HMAC."""
    L.append("FPO-1", "note", {"n": 1})
    b = L.blocks[0]
    b["payload"]["data"]["n"] = 2
    b["hash"] = _h({k: b[k] for k in ("index", "ts", "prev", "payload", "sig")})
    assert L.verify() is False


def test_open_escrow_validations_and_block(L):
    L.open_escrow("FPO-1", "E1", "F001", 1000, "B")
    assert L.escrows["E1"] == dict(buyer="FPO-1", farmer="F001", amount=1000, min_grade="B", state="FUNDED")
    blk = L.blocks[-1]["payload"]
    assert blk["kind"] == "escrow_funded" and blk["by"] == "FPO-1"
    assert blk["data"] == dict(id="E1", farmer="F001", amount=1000, min_grade="B")
    with pytest.raises(LedgerError, match="duplicate escrow id"):
        L.open_escrow("FPO-1", "E1", "F002", 5, "A")
    assert len(L.blocks) == 1 and L.escrows["E1"]["farmer"] == "F001"


@pytest.mark.parametrize("amount", [0, -1, -0.01])
def test_open_escrow_rejects_non_positive_amounts(L, amount):
    with pytest.raises(LedgerError, match="amount must be positive"):
        L.open_escrow("FPO-1", "E1", "F001", amount, "B")
    assert "E1" not in L.escrows and L.blocks == []


def test_open_escrow_accepts_smallest_positive_amount(L):
    L.open_escrow("FPO-1", "E1", "F001", 0.01, "B")
    assert L.escrows["E1"]["amount"] == 0.01


@pytest.mark.parametrize("promised,delivered,state", [
    ("B", "A", "RELEASED"),      # better than promised
    ("B", "B", "RELEASED"),      # exactly the promised grade (boundary)
    ("B", "C", "DISPUTED"),      # worse
    ("A", "B", "DISPUTED"),
    ("C", "A", "RELEASED"),
    ("C", "C", "RELEASED"),
])
def test_grade_threshold(L, promised, delivered, state):
    L.open_escrow("FPO-1", "E1", "F001", 100, promised)
    assert L.confirm_delivery("FPO-1", "E1", delivered, 10) == state
    assert L.escrows["E1"]["state"] == state
    last = L.blocks[-1]["payload"]
    assert last["kind"] == "escrow_" + state.lower() and last["by"] == "FPO-1"
    assert last["data"] == dict(id="E1", grade=delivered, qty_kg=10)


def test_confirm_delivery_error_paths(L):
    with pytest.raises(LedgerError, match="unknown escrow"):
        L.confirm_delivery("FPO-1", "nope", "A", 1)
    L.open_escrow("FPO-1", "E1", "F001", 100, "B")
    with pytest.raises(LedgerError, match="only the funding buyer"):
        L.confirm_delivery("AgriBank", "E1", "A", 1)
    assert L.escrows["E1"]["state"] == "FUNDED" and len(L.blocks) == 1
    L.confirm_delivery("FPO-1", "E1", "A", 1)
    with pytest.raises(LedgerError, match="escrow is RELEASED, expected FUNDED"):
        L.confirm_delivery("FPO-1", "E1", "A", 1)       # cannot release twice


def test_resolve_dispute_flow_and_pct_bounds(L):
    L.open_escrow("FPO-1", "E1", "F001", 100, "A")
    with pytest.raises(LedgerError, match="escrow is FUNDED, expected DISPUTED"):
        L.resolve_dispute("Arbiter", "E1", 50)
    with pytest.raises(LedgerError, match="unknown escrow"):
        L.resolve_dispute("Arbiter", "zzz", 50)
    L.confirm_delivery("FPO-1", "E1", "C", 1)
    for bad in (-0.1, 100.1, 1000):
        with pytest.raises(LedgerError, match="pct out of range"):
            L.resolve_dispute("Arbiter", "E1", bad)
        assert L.escrows["E1"]["state"] == "DISPUTED"
    L.resolve_dispute("Arbiter", "E1", 0)                # 0 is allowed
    assert L.escrows["E1"]["state"] == "SETTLED"
    assert L.blocks[-1]["payload"] == {"kind": "escrow_settled", "data": dict(id="E1", farmer_pct=0), "by": "Arbiter"}


@pytest.mark.parametrize("pct", [0, 100, 60.5])
def test_resolve_dispute_accepts_inclusive_bounds(L, pct):
    L.open_escrow("FPO-1", "E1", "F001", 100, "A")
    L.confirm_delivery("FPO-1", "E1", "C", 1)
    L.resolve_dispute("Arbiter", "E1", pct)
    assert L.escrows["E1"]["state"] == "SETTLED"


def test_disburse_checks_and_block(L):
    L.disburse("Agency", "PM-KISAN", "2026-Q3", "F001", 2000, True)
    assert ("PM-KISAN", "2026-Q3", "F001") in L.disbursed
    assert L.blocks[-1]["payload"] == {
        "kind": "dbt_disbursed", "by": "Agency",
        "data": dict(scheme="PM-KISAN", period="2026-Q3", farmer="F001", amount=2000)}
    with pytest.raises(LedgerError, match="duplicate disbursement"):
        L.disburse("Agency", "PM-KISAN", "2026-Q3", "F001", 2000, True)
    for args in (("OTHER", "2026-Q3", "F001"), ("PM-KISAN", "2026-Q4", "F001"), ("PM-KISAN", "2026-Q3", "F002")):
        L.disburse("Agency", *args, 1, True)             # each key component distinguishes a payment
    assert len(L.blocks) == 4


def test_disburse_unverified_is_checked_before_duplicate_and_not_recorded(L):
    with pytest.raises(LedgerError, match="farmer identity not verified"):
        L.disburse("Agency", "S", "P", "F001", 5, False)
    assert L.disbursed == set() and L.blocks == []
    L.disburse("Agency", "S", "P", "F001", 5, True)
    with pytest.raises(LedgerError, match="farmer identity not verified"):
        L.disburse("Agency", "S", "P", "F001", 5, False)  # unverified wins over duplicate


def test_reconcile_shortfalls_rounding_and_overpayment(L):
    L.open_escrow("FPO-1", "E1", "F001", 1000, "B")
    L.confirm_delivery("FPO-1", "E1", "A", 1)             # released -> owed 1000
    L.open_escrow("FPO-1", "E2", "F002", 300, "A")
    L.confirm_delivery("FPO-1", "E2", "C", 1)             # disputed -> not owed
    L.open_escrow("FPO-1", "E3", "F003", 50, "A")         # still funded -> not owed
    L.disburse("Agency", "S", "P", "F001", 200.555, True)
    L.disburse("Agency", "S", "P", "F004", 100, True)
    out = L.reconcile({"F001": 1000, "F004": 100.5})
    assert out == {"F001": 200.56}                        # rounded to 2dp, overpaid F004 excluded
    assert L.reconcile({"F001": 1200.555, "F004": 100}) == {}      # exact credit -> no shortfall
    assert L.reconcile({}) == {"F001": 1200.56, "F004": 100}


def test_reconcile_exact_credit_is_not_a_shortfall_and_sums_per_farmer(L):
    L.disburse("Agency", "S1", "P", "F001", 10, True)
    L.disburse("Agency", "S2", "P", "F001", 15, True)
    assert L.reconcile({}) == {"F001": 25}
    assert L.reconcile({"F001": 25}) == {}
    assert L.reconcile({"F001": 24.99}) == {"F001": 0.01}
    assert Ledger().reconcile({"F": 1}) == {}


def test_reconcile_does_not_mutate_bank_input(L):
    L.disburse("Agency", "S", "P", "F001", 10, True)
    bank = {"F001": 4}
    L.reconcile(bank)
    assert bank == {"F001": 4}


def test_full_lifecycle_chain_still_verifies(L):
    L.open_escrow("FPO-1", "E1", "F001", 1000, "B")
    L.confirm_delivery("FPO-1", "E1", "C", 400)
    L.resolve_dispute("Arbiter", "E1", 60)
    L.disburse("Agency", "S", "P", "F002", 1, True)
    assert [b["payload"]["kind"] for b in L.blocks] == [
        "escrow_funded", "escrow_disputed", "escrow_settled", "dbt_disbursed"]
    assert L.verify()


# ---- source bugs: state is mutated BEFORE the authorising append() can raise ----------------------

@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="BUG ledger.py:open_escrow stores the escrow before append(); a non-member buyer gets "
                          "LedgerError yet the escrow stays in self.escrows with no block recording it")
def test_open_escrow_by_non_member_leaves_no_state():
    led = Ledger()
    with pytest.raises(LedgerError):
        led.open_escrow("Mallory", "E1", "F001", 100, "B")
    assert led.escrows == {} and led.blocks == []


@pytest.mark.xfail(strict=True, raises=LedgerError,
                   reason="BUG ledger.py:disburse adds the key to self.disbursed before append(); a non-member "
                          "agency's rejected payment permanently blocks the real agency (duplicate disbursement)")
def test_disburse_by_non_member_does_not_burn_the_payment_key(L):
    with pytest.raises(LedgerError):
        L.disburse("Mallory", "S", "P", "F001", 10, True)
    L.disburse("Agency", "S", "P", "F001", 10, True)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="BUG ledger.py:resolve_dispute sets state=SETTLED before append(); a non-member "
                          "'arbiter' is rejected but the dispute is already marked SETTLED with no block")
def test_resolve_dispute_by_non_member_keeps_dispute_open(L):
    L.open_escrow("FPO-1", "E1", "F001", 100, "A")
    L.confirm_delivery("FPO-1", "E1", "C", 1)
    with pytest.raises(LedgerError):
        L.resolve_dispute("Mallory", "E1", 50)
    assert L.escrows["E1"]["state"] == "DISPUTED"


# ---- survivors of the mutation pass ---------------------------------------------------------------

def test_verify_rejects_rehashed_block_with_wrong_index(L):
    """index is covered by the hash but NOT the HMAC, so only the explicit index check catches a re-hashed block."""
    L.append("FPO-1", "note", {"n": 1})
    L.append("Agency", "note", {"n": 2})
    b = L.blocks[1]
    b["index"] = 5
    b["hash"] = _h({k: b[k] for k in ("index", "ts", "prev", "payload", "sig")})
    assert L.verify() is False


def test_reconcile_sums_multiple_released_escrows_per_farmer(L):
    L.open_escrow("FPO-1", "E1", "F001", 100, "B")
    L.open_escrow("FPO-1", "E2", "F001", 40, "B")
    L.confirm_delivery("FPO-1", "E1", "A", 1)
    L.confirm_delivery("FPO-1", "E2", "B", 1)
    L.disburse("Agency", "S", "P", "F001", 5, True)
    assert L.reconcile({}) == {"F001": 145}
    assert L.reconcile({"F001": 100}) == {"F001": 45}


def test_verify_rejects_rehashed_block_with_wrong_prev_link(L):
    """prev is covered by the hash but NOT the HMAC, so only the explicit link check catches a re-hashed block."""
    L.append("FPO-1", "note", {"n": 1})
    L.append("Agency", "note", {"n": 2})
    b = L.blocks[1]
    b["prev"] = GENESIS
    b["hash"] = _h({k: b[k] for k in ("index", "ts", "prev", "payload", "sig")})
    assert L.verify() is False

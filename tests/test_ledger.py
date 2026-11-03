import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fpdlt.ledger import Ledger, LedgerError  # noqa: E402


def make():
    L = Ledger()
    for org in ("FPO-1", "AgriBank", "Agency", "Arbiter"):
        L.register(org, org.encode() + b"-secret")
    return L


class LedgerTests(unittest.TestCase):
    def test_chain_verifies_and_detects_tampering(self):
        L = make()
        L.open_escrow("FPO-1", "E1", "F001", 1000, "B")
        L.confirm_delivery("FPO-1", "E1", "A", 500)
        self.assertTrue(L.verify())
        L.blocks[0]["payload"]["data"]["amount"] = 1
        self.assertFalse(L.verify())

    def test_non_member_cannot_append(self):
        with self.assertRaises(LedgerError):
            make().append("Mallory", "x", {})

    def test_escrow_release_on_good_grade(self):
        L = make()
        L.open_escrow("FPO-1", "E1", "F001", 1000, "B")
        self.assertEqual(L.confirm_delivery("FPO-1", "E1", "B", 400), "RELEASED")

    def test_escrow_dispute_then_settle(self):
        L = make()
        L.open_escrow("FPO-1", "E1", "F001", 1000, "B")
        self.assertEqual(L.confirm_delivery("FPO-1", "E1", "C", 400), "DISPUTED")
        L.resolve_dispute("Arbiter", "E1", 60)
        with self.assertRaises(LedgerError):
            L.resolve_dispute("Arbiter", "E1", 60)  # already settled

    def test_only_funding_buyer_confirms(self):
        L = make()
        L.open_escrow("FPO-1", "E1", "F001", 1000, "B")
        with self.assertRaises(LedgerError):
            L.confirm_delivery("AgriBank", "E1", "A", 1)

    def test_dbt_blocks_duplicates_and_unverified(self):
        L = make()
        L.disburse("Agency", "PM-KISAN", "2026-Q3", "F001", 2000, True)
        with self.assertRaises(LedgerError):
            L.disburse("Agency", "PM-KISAN", "2026-Q3", "F001", 2000, True)
        with self.assertRaises(LedgerError):
            L.disburse("Agency", "PM-KISAN", "2026-Q3", "F002", 2000, False)
        L.disburse("Agency", "PM-KISAN", "2026-Q4", "F001", 2000, True)  # new period ok

    def test_reconcile_flags_missing_credit(self):
        L = make()
        L.open_escrow("FPO-1", "E1", "F001", 1000, "B")
        L.confirm_delivery("FPO-1", "E1", "A", 400)
        L.disburse("Agency", "S", "P", "F002", 500, True)
        self.assertEqual(L.reconcile({"F001": 1000}), {"F002": 500})


if __name__ == "__main__":
    unittest.main()

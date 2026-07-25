import unittest
from production_cell import CellState, GateResult, OverrideReceipt, PlaybookPatch, ProductionCell, RightsObject, Verdict

GOOD_RIGHTS = RightsObject(
    source_owner="Captain",
    permission_basis="owned source material",
    commercial_use=True,
    allowed_transformations=("edit", "publish"),
    evidence=("rights://owned-source-1",),
)

class ProductionCellTests(unittest.TestCase):
    def ready(self, public=False):
        cell = ProductionCell("cell-1", "intent-1", public_release=public, rights=GOOD_RIGHTS if public else None)
        cell.begin()
        cell.submit_for_assurance()
        return cell

    def test_passed_gate_verifies(self):
        cell = self.ready()
        cell.record_gate(GateResult("qa", Verdict.PASS, ("evidence://qa",)))
        self.assertEqual(cell.state, CellState.VERIFIED)

    def test_failed_gate_blocks(self):
        cell = self.ready()
        cell.record_gate(GateResult("qa", Verdict.FAIL, reason="broken output"))
        self.assertEqual(cell.state, CellState.BLOCKED)
        with self.assertRaises(ValueError):
            cell.authorize()

    def test_unavailable_gate_does_not_fail_open(self):
        cell = self.ready()
        cell.record_gate(GateResult("reviewer", Verdict.UNAVAILABLE))
        self.assertEqual(cell.state, CellState.WAITING_FOR_ASSURANCE)
        with self.assertRaises(ValueError):
            cell.authorize()

    def test_public_release_requires_rights(self):
        cell = ProductionCell("cell", "intent", public_release=True)
        cell.begin(); cell.submit_for_assurance()
        cell.record_gate(GateResult("qa", Verdict.PASS))
        with self.assertRaisesRegex(ValueError, "rights object"):
            cell.authorize()

    def test_incomplete_rights_are_rejected(self):
        rights = RightsObject("", "", False, (), evidence=())
        cell = ProductionCell("cell", "intent", public_release=True, rights=rights)
        cell.begin(); cell.submit_for_assurance()
        cell.record_gate(GateResult("qa", Verdict.PASS))
        with self.assertRaisesRegex(ValueError, "rights gate failed"):
            cell.authorize()

    def test_override_must_cover_every_open_risk(self):
        cell = self.ready()
        cell.record_gate(GateResult("qa", Verdict.FAIL))
        cell.record_gate(GateResult("policy", Verdict.UNAVAILABLE))
        receipt = OverrideReceipt.create("captain-zed", ["qa"], "known bounded risk")
        with self.assertRaisesRegex(ValueError, "policy"):
            cell.accept_risk(receipt)

    def test_explicit_non_rights_risk_can_be_accepted(self):
        cell = self.ready()
        cell.record_gate(GateResult("qa", Verdict.FAIL))
        cell.accept_risk(OverrideReceipt.create("captain-zed", ["qa"], "controlled prototype"))
        self.assertEqual(cell.state, CellState.AUTHORIZED)

    def test_rights_failure_is_not_overrideable(self):
        cell = ProductionCell("cell", "intent", public_release=True)
        cell.begin(); cell.submit_for_assurance()
        cell.record_gate(GateResult("rights", Verdict.FAIL))
        with self.assertRaisesRegex(ValueError, "cannot be overridden"):
            cell.accept_risk(OverrideReceipt.create("captain-zed", ["rights"], "exception request"))

    def test_execution_requires_authorization(self):
        with self.assertRaises(ValueError):
            self.ready().execute()

    def test_full_path_and_receipt(self):
        cell = self.ready(public=True)
        cell.record_gate(GateResult("qa", Verdict.PASS, ("artifact://qa",)))
        cell.record_gate(GateResult("rights", Verdict.PASS, ("rights://owned-source-1",)))
        cell.authorize(); cell.execute(); cell.observe({"accepted": True, "cost_cad": 0.03})
        receipt = cell.receipt()
        self.assertEqual(receipt["state"], "observed")
        self.assertEqual(len(receipt["receipt_hash"]), 64)

    def test_playbook_requires_independent_reviewer(self):
        patch = PlaybookPatch("p", "hooks", ("metric://1",), "+ rule", "same", "same", True, True)
        self.assertFalse(patch.promotable())

    def test_playbook_rejects_protected_target(self):
        patch = PlaybookPatch("p", "constitution", ("metric://1",), "+ rule", "trainer", "auditor", True, True)
        self.assertFalse(patch.promotable({"constitution", "editorial-standards"}))

    def test_playbook_needs_replay_and_canary(self):
        patch = PlaybookPatch("p", "hooks", ("metric://1",), "+ rule", "trainer", "auditor", True, False)
        self.assertFalse(patch.promotable())

if __name__ == "__main__":
    unittest.main()

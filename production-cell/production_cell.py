from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable


class CellState(str, Enum):
    PLANNED = "planned"
    WORKING = "working"
    WAITING_FOR_ASSURANCE = "waiting_for_assurance"
    BLOCKED = "blocked"
    VERIFIED = "verified"
    AUTHORIZED = "authorized"
    EXECUTED = "executed"
    OBSERVED = "observed"


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    verdict: Verdict
    evidence: tuple[str, ...] = ()
    reason: str = ""
    sovereign: bool = True


@dataclass(frozen=True)
class RightsObject:
    source_owner: str
    permission_basis: str
    commercial_use: bool
    allowed_transformations: tuple[str, ...]
    attribution_required: bool = False
    evidence: tuple[str, ...] = ()

    def validate_public_release(self) -> list[str]:
        errors: list[str] = []
        if not self.source_owner.strip():
            errors.append("source owner missing")
        if not self.permission_basis.strip():
            errors.append("permission basis missing")
        if not self.commercial_use:
            errors.append("commercial/public use not authorized")
        if not self.allowed_transformations:
            errors.append("allowed transformations missing")
        if not self.evidence:
            errors.append("rights evidence missing")
        return errors


@dataclass(frozen=True)
class OverrideReceipt:
    captain_id: str
    accepted_risks: tuple[str, ...]
    reason: str
    created_at: str
    receipt_hash: str

    @classmethod
    def create(cls, captain_id: str, accepted_risks: Iterable[str], reason: str) -> "OverrideReceipt":
        risks = tuple(sorted(set(accepted_risks)))
        created_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "captain_id": captain_id,
            "accepted_risks": risks,
            "reason": reason,
            "created_at": created_at,
        }
        receipt_hash = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()
        return cls(captain_id, risks, reason, created_at, receipt_hash)


@dataclass
class ProductionCell:
    cell_id: str
    intent_id: str
    public_release: bool = False
    required_gate_ids: tuple[str, ...] = ()
    state: CellState = CellState.PLANNED
    gate_results: list[GateResult] = field(default_factory=list)
    rights: RightsObject | None = None
    override: OverrideReceipt | None = None
    telemetry: list[dict[str, Any]] = field(default_factory=list)

    def begin(self) -> None:
        self._require(CellState.PLANNED)
        self.state = CellState.WORKING

    def submit_for_assurance(self) -> None:
        self._require(CellState.WORKING)
        self.state = CellState.WAITING_FOR_ASSURANCE

    def record_gate(self, result: GateResult) -> None:
        if self.state not in {
            CellState.WAITING_FOR_ASSURANCE,
            CellState.BLOCKED,
            CellState.VERIFIED,
        }:
            raise ValueError("gate results may only be recorded during assurance")
        self.gate_results = [g for g in self.gate_results if g.gate_id != result.gate_id]
        self.gate_results.append(result)
        self.state = self._assurance_state()

    def authorize(self) -> None:
        if self.public_release:
            if self.rights is None:
                raise ValueError("public release requires a rights object")
            rights_errors = self.rights.validate_public_release()
            if rights_errors:
                raise ValueError("rights gate failed: " + "; ".join(rights_errors))

        if self.state != CellState.VERIFIED:
            raise ValueError(f"cannot authorize from state {self.state.value}")
        self.state = CellState.AUTHORIZED

    def accept_risk(self, receipt: OverrideReceipt) -> None:
        failed = {g.gate_id for g in self.gate_results if g.verdict == Verdict.FAIL}
        unavailable = {g.gate_id for g in self.gate_results if g.verdict == Verdict.UNAVAILABLE}
        reported = {g.gate_id for g in self.gate_results}
        missing_reports = set(self.required_gate_ids) - reported
        open_risks = failed | unavailable | missing_reports
        missing = open_risks - set(receipt.accepted_risks)
        if missing:
            raise ValueError("override does not cover risks: " + ", ".join(sorted(missing)))

        if self.public_release:
            if self.rights is None or self.rights.validate_public_release():
                raise ValueError("rights/provenance failures cannot be overridden")

        self.override = receipt
        self.state = CellState.AUTHORIZED

    def execute(self) -> None:
        self._require(CellState.AUTHORIZED)
        self.state = CellState.EXECUTED

    def observe(self, metrics: dict[str, Any]) -> None:
        self._require(CellState.EXECUTED)
        self.telemetry.append({"observed_at": datetime.now(timezone.utc).isoformat(), **metrics})
        self.state = CellState.OBSERVED

    def receipt(self) -> dict[str, Any]:
        payload = _serialize(asdict(self))
        payload["receipt_hash"] = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()
        return payload

    def _assurance_state(self) -> CellState:
        if not self.gate_results:
            return CellState.WAITING_FOR_ASSURANCE
        if any(g.verdict == Verdict.FAIL for g in self.gate_results):
            return CellState.BLOCKED
        if any(g.verdict == Verdict.UNAVAILABLE for g in self.gate_results):
            return CellState.WAITING_FOR_ASSURANCE
        reported = {g.gate_id for g in self.gate_results}
        if set(self.required_gate_ids) - reported:
            return CellState.WAITING_FOR_ASSURANCE
        return CellState.VERIFIED

    def _require(self, expected: CellState) -> None:
        if self.state != expected:
            raise ValueError(f"expected {expected.value}, got {self.state.value}")


@dataclass(frozen=True)
class PlaybookPatch:
    patch_id: str
    target: str
    evidence_ids: tuple[str, ...]
    diff: str
    proposer_identity: str
    reviewer_identity: str
    replay_passed: bool
    canary_passed: bool

    def promotable(self, protected_targets: Iterable[str] = ()) -> bool:
        return (
            self.target not in set(protected_targets)
            and bool(self.evidence_ids)
            and self.proposer_identity != self.reviewer_identity
            and self.replay_passed
            and self.canary_passed
            and bool(self.diff.strip())
        )


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(_serialize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

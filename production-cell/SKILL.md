---
name: production-cell
description: Build and operate a governed GLEE production cell with deterministic-first workers, sovereign assurance gates, rights/provenance enforcement, outcome telemetry, and audited playbook learning.
disable-model-invocation: true
allowed-tools: Bash(python *), Bash(pytest *), Bash(git *), Read, Edit, Write, Grep, Glob, Task
argument-hint: "<intent or existing workflow>"
---

# GLEE Production Cell v1

Use this skill when a Captain intent must become a repeatable production workflow rather than a one-off agent chain.

## Contract

A Production Cell is:

```text
Captain Intent
  -> Planner
  -> deterministic and AI workers
  -> technical verifier
  -> domain reviewer
  -> policy and rights gates
  -> authorized executor
  -> telemetry collector
  -> governed learning proposal
  -> independent review, replay, canary, promote or rollback
```

The cell must reuse GLEE's existing intent, MCS/model selection, job, receipt, notification, provenance, and callback systems. Do not create a parallel state store when a canonical GLEE object already exists.

## Non-negotiable invariants

1. **Fail closed.** `UNAVAILABLE` means `WAITING_FOR_ASSURANCE`, never PASS.
2. **Verifier sovereignty.** Throughput, deadlines, quotas, posting schedules, or empty queues cannot silently reverse a failed gate.
3. **Conversation authority.** Explicit Captain approval in the governing conversation may accept a bounded non-rights risk. It must create an `OverrideReceipt` naming every accepted risk.
4. **Rights are prerequisite.** Public release requires a valid `RightsObject`. Missing or invalid rights/provenance cannot be bypassed by a normal quality-risk override.
5. **Deterministic first.** Use parsers, schemas, hashes, tests, probes, static analysis, media inspection, and local programs before spending model tokens.
6. **Independent learning review.** A playbook proposer cannot approve its own patch. Protected targets such as the Constitution and editorial standards cannot be modified through the playbook path.
7. **Measured promotion.** Learning patches require evidence, historical replay, a bounded canary, and rollback capability.
8. **Receipts everywhere.** Gate evidence, model/provider selections, costs, overrides, execution results, and observed outcomes must be traceable.

## Canonical states

- `planned`
- `working`
- `waiting_for_assurance`
- `blocked`
- `verified`
- `authorized`
- `executed`
- `observed`

Do not compress `waiting_for_assurance`, `blocked`, and `verified` into a generic finished state.

## Build procedure

### 1. Resolve the intent

Create or locate the Durable Intent Object. Record success criteria, public/private release status, authority boundaries, risk class, budget/quota limits, and expected telemetry.

### 2. Compile the cell

Use MCS to select the cheapest sufficient complete stack. Prefer local/deterministic lanes, then free or near-free models, then paid premium models only where judgment quality justifies them.

Every role must declare:

- input and output schema
- deterministic tools available
- model class and effort ceiling
- write scope
- timeout and retry policy
- escalation target
- evidence it must emit

### 3. Execute workers

Workers may generate, transform, inspect, or package artifacts. A worker never marks its own output verified merely because execution succeeded.

### 4. Run assurance

Record explicit `GateResult` objects for technical quality, domain quality, policy, security, provenance/rights, and any task-specific gates.

- Any FAIL -> `blocked`
- Any UNAVAILABLE and no FAIL -> `waiting_for_assurance`
- All required gates PASS -> `verified`

### 5. Authorize and execute

Only `verified` work may become `authorized`, except when the Captain provides a complete bounded-risk override receipt. Public release additionally requires a valid rights object.

### 6. Observe outcomes

Collect useful outcome telemetry, not vanity output counts. Examples include acceptance rate, regressions, human corrections, retention, revenue, latency, total token and compute cost, false accepts, false rejects, and rollback frequency.

Optimize verified useful outcome per total resource cost, including quota use and human repair time.

### 7. Govern learning

The Trainer proposes a `PlaybookPatch` containing evidence IDs and a diff. A distinct reviewer performs hostile review. Replay the patch against historical cases, run a canary, compare metrics, then promote or rollback. Never auto-edit protected doctrine through this path.

## GLEE core integration target

The sovereign runtime implementation should live under:

```text
/home/zed/core/glee/glee_pkg/production_cell/
```

Expected adapters:

- Durable Intent Object adapter
- MCS/model-effort selector adapter
- job/worker dispatcher adapter
- assurance and evidence receipt adapter
- provenance/rights object adapter
- Captain conversation approval adapter
- notification and room/terminal projection adapter
- outcome telemetry adapter
- governed playbook registry adapter

This repository contains the portable reference state machine in `production_cell.py`. Integrate it by adapting canonical GLEE objects; do not duplicate canonical ledgers.

## Verification

Run:

```bash
cd production-cell
python -m unittest -v test_production_cell.py
```

Required adversarial cases include unavailable verifiers, failed gate blocking, missing rights, incomplete override coverage, non-overridable rights failures, unauthorized execution, independent learning review, protected-target rejection, replay failure, and canary failure.

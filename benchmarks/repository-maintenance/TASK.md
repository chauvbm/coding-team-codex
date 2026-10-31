# Repository maintenance contract s1

Baseline: unmodified scripts and governance defaults from coding-team-codex commit `6055037c`. Implement two independent work items. Preserve existing public functions and init/update/check behavior. Use Python standard library, no new host configuration or dependencies.

## Ledger operations

In `scripts/task_ledger.py`, add CLI `record-review` accepting `--ledger`, `--input` (one review JSON object), `--expected-revision` integer, and `--reason`. Append the supplied review to the current ledger in a single locked transaction, preserving all history. Validate with existing schema, transition and readiness before atomic save; increment revision/audit once. Unknown review fields must be rejected. Successful save returns 0 even on readiness HOLD; invalid/stale writes return 2 without modifying the file. Existing stale-version and independent-QA readiness rules remain.

Add CLI `consume-budget` with `--ledger`, `--expected-revision`, `--reason`, `--counter` (one of revisions/repairs/diagnostics/recovery_total), `--amount` positive integer default 1, and `--phase` reserve/use/both default both. Reserve increments reserved; use increments used only within reserved; both increments both. Validate existing limits/readiness and retain excess as HOLD rather than resetting counters. Use the same transactional behavior. Counter names, phase or amounts outside the contract must fail without changing state. Two simultaneous writes with the same revision must produce exactly one success and one stale rejection.

## Safe evaluation export

In `scripts/export_evaluation_inputs.py`, preserve the exporter API and CLI, including omission of tests/oracles/results. Reject a symbolic link anywhere in the operational resources being exported (`SKILL.md`, references, scripts, agents), including a link to another in-root file or a broken link. Reject linked resource directories as well. Do not follow links while checking. Reject before creating the destination or copying any resource; report ValueError/API or nonzero CLI without modifying source or external targets. Normal files still export. Do not require a complete security sandbox, defend races, or modify native permissions.

## Execution protocol

Participants receive this contract and baseline, without acceptance tests, reference implementations, historical outputs or peer verdicts before initial review. Write only inside the assigned isolated workspace. Self-checks are allowed; do not read coordinator acceptance or other modes. SOLO uses one coder and self-checks; AUTO adds independent final QA; FULL_TEAM reviews the plan with Architect/Developer/QA, then assigns the two modules to separate Developers and performs integrated independent QA. A required plan gate must pass before implementation. Revisions, ownership transfers and material findings remain recorded. No hidden-test feedback repair.

The coordinator freezes acceptance before dispatch and evaluates the first delivered snapshot. Store timing as observations, not controlled latency estimates. Missing token/model telemetry is null. Preserve ties and losses. This is one small task from this repository, not a production study or an unbiased sample of all coding work.

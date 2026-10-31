# Optional persistent task ledger

Use `scripts/task_ledger.py` for long, resumed, parallel or gated tasks when a prose ledger is too easy to lose. Simple tasks may keep concise prose. This helper stores and checks records; it does not dispatch agents, schedule work, inspect source or run tests. Numeric allowances come from [governance-defaults.json](governance-defaults.json), never a second set of constants.

Keep real task ledgers outside the public working tree, or under a deliberately ignored private location. They can contain conversation/evidence references and should not be committed with the skill. `operating_state: PAUSED` preserves a quota or user pause while blocking gate and delivery readiness until an authorized resume is recorded.

## Commands and results

```powershell
python scripts/task_ledger.py init --ledger .task/ledger.json --input baseline.json --reason "record task baseline"
python scripts/task_ledger.py update --ledger .task/ledger.json --input candidate.json --expected-revision 0 --reason "record independent review"
python scripts/task_ledger.py check --ledger .task/ledger.json
python scripts/task_ledger.py check --ledger .task/ledger.json --stage gate
```

`init` accepts a document without `revision` or `audit`. It refuses any existing ledger, including a corrupt one. For `update`, read the current document, preserve its helper-managed revision and audit unchanged, edit the intended fields and supply that document as the candidate. The expected revision prevents a stale writer from overwriting another update. The helper increments it and appends the audit event while holding the OS lock.

`init` and `update` return exit 0 after a structurally valid record is saved, including records on HOLD. `check` returns 0 only for PASS at the selected `--stage gate|delivery` (default `delivery`), 1 for a valid HOLD at that stage, and 2 for malformed JSON, invalid schema, invalid paths or storage errors. Mutating commands return 2 for rejected writes. JSON output distinguishes `valid`, `gate`, `delivery`, `gate_blockers` and delivery `blockers`. Always run `check` before using the record as readiness evidence; a successful save is not permission to act. A caller-supplied `gate`, delivery claim or `operating_state: PASS` cannot supply approvals.

`gate` checks current required plan/scope approvals and material findings; `delivery` additionally requires current independent `FinalQA` evidence for every scope. AUTO tasks may leave `required_reviews` empty. Gated tasks must name Architect, Developer and QA for each scope. A successful plan gate does not replace final QA.

## Small schema

The initial document below deliberately has no approvals and therefore produces delivery HOLD. Replace the project root with the actual existing project directory.

```json
{
  "schema_version": 1,
  "task_id": "example-task",
  "project_root": "D:/skill/coding-team",
  "operating_state": "ACTIVE",
  "baseline": {
    "level": "L2",
    "spec": "s1",
    "plan": "p1",
    "snapshot": "identified-stable-tree",
    "gated": false,
    "scopes": ["all"],
    "acceptance": ["Describe observable behavior and verification"],
    "writers": ["developer-identity"],
    "required_reviews": []
  },
  "counters": {
    "revisions": {"reserved": 0, "used": 0},
    "repairs": {"reserved": 0, "used": 0},
    "diagnostics": {"reserved": 0, "used": 0},
    "recovery_total": {"reserved": 0, "used": 0},
    "defects": {},
    "recoveries": {}
  },
  "issues": [],
  "reviews": [],
  "transfers": [],
  "review_deadlines": {},
  "work_items": [],
  "continuation": null
}
```

- Required review: `{"role":"QA","reviewer":"qa-identity","scope":"all"}`. A gated scope also needs Architect and Developer entries.
- Review: `{"id":"qa1","reviewer":"qa-identity","role":"FinalQA","scope":"all","spec":"s1","plan":"p1","snapshot":"identified-stable-tree","verdict":"APPROVED","evidence":"specific check/result reference","directly_verified":true,"issues":[]}`. Use `QA` for a plan approval, `FinalQA` for final integrated verification. Rejection uses `REJECTED`. Review IDs are unique; append subsequent verdicts instead of rewriting old ones. The latest applicable verdict controls each responsibility. QA and FinalQA must be outside the recorded writer set; their independence is conservatively task-wide. Architect and Developer may accept the design and later implement it. An original Developer finding may receive their own attributed confirmation after repair, but material closure additionally requires a current independent QA/FinalQA review listing the issue.
- Issue: `{"id":"bug1","aliases":[],"originators":[{"reviewer":"qa-identity","statement":"original failure and dissent"}],"scope":"all","severity":"MAJOR","status":"OPEN","closure_criteria":"specific repair evidence required"}`. Severity is BLOCKER, MAJOR, MINOR or SUGGESTION; status is OPEN, CONTESTED or RESOLVED. Resolution adds `closed_by` naming a current review explicitly listing this issue. Every original dissenter must directly confirm closure, or have a valid successor do so. An APPROVED summary without those confirmations cannot hide a material issue.
- Work item: `{"id":"work1","owner":"developer-identity","status":"ACTIVE","files":["src/example.py"]}`. Other statuses are PENDING, DONE and CANCELLED. Owners of files must be retained in `baseline.writers`. Ownership names explicit files, with one active work item per normalized path. Absolute paths, drive-relative paths, parent traversal, wildcard paths, directories and symlink escapes are rejected. Ownership checks do not acquire filesystem write locks; the coordinator must stop/await a writer before transfer.
- Counter maps `defects` and `recoveries` map stable defect/role-or-operation IDs to the same `{reserved,used}` shape. Both values are cumulative and never decrease; `used` cannot exceed `reserved`. Reserve before dispatch. Cancellation retains its reservation. The total recovery counters must cover all individual recovery counters. The helper cannot observe whether a dispatch was omitted from the record.

The task identity, root, level, writer attribution, existing scopes, required gate and existing review responsibilities cannot be reset through updates. Reviews and transfers are append-only. Issues cannot be deleted, and original statements, aliases, severity, scope and closure criteria are preserved. Use a new issue for a distinct cause. A changed baseline requires a fresh Spec/Plan/snapshot tuple, and historical tuples cannot be reused to revive old approvals. A current explicit review entry can confirm applicability at the new tuple. The helper conservatively invalidates all tuple-bound approvals when that tuple changes; it does not infer cosmetic equivalence.

A material issue's historical `closed_by` approval is insufficient if that closer subsequently rejects the issue. The latest applicable issue-specific verdict must accept it for the closer, every original originator and every reviewer who records a current issue rejection. Responsibilities are distinguished by reviewer and role; an approval in another role does not erase dissent. A valid scoped successor may supply the former reviewer's reassessment, while all original verdicts remain recorded.

Audit entries preserve baseline, counter and issue-disposition history along with the reason and timestamp. The audit lives inside the same JSON document as current state. Same-directory temporary writes, flush/fsync and atomic replace prevent partial state/audit transactions; the existing policy helper supplies the OS lock. Failed writes preserve the previous file and release the lock. This is local process coordination, not a distributed database or tamper-proof log. Direct file modification can bypass the CLI.

## Controlled reviewer responsibility transfer

Preserve the original required reviewer and append a scoped transfer; do not edit their rejection or appoint a replacement by changing the required-review entry. Example:

```json
{
  "id": "replacement1",
  "role": "QA",
  "scope": "all",
  "from": "original-reviewer",
  "to": "independent-successor",
  "reason": "Recorded concrete reason the predecessor is unavailable",
  "unavailable": true,
  "spec": "s1",
  "plan": "p1",
  "snapshot": "identified-stable-tree",
  "recovery_key": "QA/all",
  "attempt": 1
}
```

Record the reserved/used recovery attempt under `counters.recoveries["QA/all"]` and in the totals. One attempt cannot appoint multiple successors. Current numeric recovery allowances still apply; continuation for repair does not extend recovery. The successor must be outside the writer set and append their own current, directly verified verdict with specific evidence and the inherited issue IDs. Missing, blind, stale, self-reviewing or over-budget replacement does not supply approval. Original dissent and review history remain visible after valid closure. Unavailable acceptance stays HOLD until reassessment actually occurs. The helper validates recorded relationships; the coordinator must verify actual independence, unavailability and evidence.

Before dispatch, declare the original deadline under the same recovery key, for example `review_deadlines["QA/all"] = {"reviewer":"original-reviewer","role":"QA","scope":"all","at":"2026-10-31T10:01:00+00:00"}`. That entry cannot be renewed, removed or reassigned on update. A valid transfer must match its original reviewer, role and scope. The successor's review must include a timezone-aware `verified_at` timestamp at or before that original deadline; missing or late verification leaves HOLD. A replacement never starts a fresh deadline. These timestamps establish a recorded relationship only: the helper does not prove when a review actually happened, enforce a running timer or authenticate clock claims.

Chained replacements for the same role/scope are unsupported and rejected as invalid records. A successor cannot appoint a further successor under a different recovery key to obtain a fresh allowance or deadline. Keep the original responsibility, recorded recovery history and deadline; if the permitted replacement cannot provide acceptance, retain HOLD.

## Authority and native enforcement boundary

An optional continuation claim has `source`, `scope` and boolean `repair_extension`. Set `scope` to the exact task ID for a repair/revision extension claim to apply. A scoped claim can record the user's existing authority for necessary repair/revision beyond checkpoints. It does not waive a gate, extend diagnostic/recovery allowances, authenticate a human message or grant external permissions. Output always reports `authority_claims_verified: false`.

All review, writer, snapshot, evidence and authority data is caller-authored. A valid or PASS document establishes internal consistency of those claims, not their truth. The coordinator must compare the claim with the actual human conversation and directly verified source/test evidence. Native tools, platform permissions and actual user authorization remain authoritative. There are no external-platform hooks or automatic human-identity checks. Corrupt or missing history requires reconstruction from saved evidence or HOLD; never initialize a replacement to assume zero history.

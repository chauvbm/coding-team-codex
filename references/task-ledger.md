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

All mutating commands return exit 0 after a structurally valid record is saved, including records on HOLD. `check` returns 0 only for PASS at the selected `--stage gate|delivery` (default `delivery`), 1 for a valid HOLD at that stage, and 2 for malformed JSON, invalid schema, invalid paths or storage errors. Mutating commands return 2 for rejected writes. JSON output distinguishes `valid`, `revision`, `verification`, `gate`, `delivery`, `gate_blockers` and delivery `blockers`. Always run `check` before using the record as readiness evidence; a successful save is not permission to act. A caller-supplied `gate`, delivery claim or `operating_state: PASS` cannot supply approvals.

`gate` checks current required plan/scope approvals and material findings; `delivery` additionally requires the baseline's verification evidence for every scope. AUTO tasks may leave `required_reviews` empty. Gated tasks must name Architect, Developer and QA with three distinct identities in each scope. Invalid initial assignments are rejected rather than saved; a valid transfer that makes effective representatives collide leaves readiness HOLD. Distinct labels do not establish independence; the coordinator must check actual identities and authorship. The same QA can perform FinalQA. A successful plan gate does not replace final verification.

## Completion and outstanding final verdicts

Delivery additionally requires every required work item to be DONE or validly cancelled. Missing `required` means true for legacy items. PENDING/ACTIVE required work holds delivery even when FinalQA approved; it does not block the plan gate. IDs cannot be removed on update and a required item cannot become optional. New audit events retain work-item snapshots, including cancellation claims.

A required CANCELLED item needs `cancellation` with nonempty `reason`, `authority`, current `spec`/`plan`/`snapshot`, and boolean `acceptance_unchanged`. If cancellation changes acceptance, update the baseline version/snapshot and acceptance criteria in the same update and obtain affected reviews again. Legacy cancelled items without that evidence remain HOLD and can be repaired through normal update. These are caller-authored scope/authority claims, not authenticated human permission or proof that an actual writer stopped.

For each scope, current FinalQA rejections remain obligations even when no issue was recorded. Each rejecting reviewer's latest current verdict must directly approve, or a valid controlled successor must provide that verdict within the original deadline and recovery allowance. Another reviewer's approval alone cannot erase the rejection. SelfCheck uses the same latest-current rejection rule. Existing material-issue closure requirements remain separate and mandatory.

## Final evidence and actual file freshness

New current `FinalQA` and `SelfCheck` entries receive helper-managed `freshness` when recorded through `init`, `update` or `record-review`. The helper hashes the actual bytes of every explicitly declared `work_items[].files` path plus optional top-level `delivery_files`, including dirty and untracked files. `delivery_files: ["report.txt"]` covers file deliverables that have no work item. Paths are portable relative paths inside the project; symlinks, Windows junction/reparse paths (including ancestors), escapes, directories, the ledger itself and its lock are not valid delivered files. The helper does not enumerate Git, the project tree or a drive. A missing declared file has an explicit null hash, allowing review of an intentional deletion. An unreadable or newly unsafe file makes delivery HOLD.

Each declared file binding includes `type` (`regular` or `missing`) and `executable_bits`: the POSIX mode mask `0o111`, or null on platforms without POSIX executable permissions and for missing files. Other permission bits, ACLs and extended attributes are outside this binding. Special files and directories are unsupported. `check` recomputes hashes and this metadata even if the ledger and baseline snapshot label have not changed. Changed bytes or executable bits invalidate final evidence and require a newly recorded direct review. Older byte-only bindings remain readable as HOLD; verify again with `record-review` to capture metadata without rewriting history.

The binding also identifies the declared work frontier: work IDs, owners, required flags and file lists. Adding work or changing ownership/files invalidates earlier final evidence. Work status and cancellation metadata are excluded from that binding, so an ACTIVE item can become DONE without another review when its content and frontier are identical. Required completion and cancellation checks still apply separately. Plan approvals retain their existing version/snapshot semantics.

An empty work/file declaration receives an explicit empty binding and can represent a non-file task; **it provides no declared file coverage**. Declare actual delivered files when file coverage is needed. Hashing proves only that those declared bytes match what the helper observed while recording evidence; it does not establish that the reviewer actually inspected them, authenticate the evidence, discover omitted deliverables or prevent concurrent writers from changing files after a check. Stop/await writers and check immediately before delivery.

Readiness output includes `file_coverage`: `scope: declared_files_only`, a unique declared-file count, `status` EMPTY/OBSERVED/UNAVAILABLE, a POSIX-executable-bit support flag and a coverage notice. OBSERVED means the declared filesystem state was read, including explicit missing-file states; review acceptance and delivery readiness are checked separately. EMPTY can still accompany a valid non-file-task PASS. UNAVAILABLE accompanies delivery HOLD when declared state cannot be checked.

Before final code verification, the coordinator must reconcile work/file declarations with the actual delivered changes, including staged, unstaged, deleted and untracked files. Use Git status/diffs when available, or compare the saved baseline in a non-Git workspace. Include relevant generated deliverables; explain excluded unrelated changes without claiming they were verified. The helper does not perform this reconciliation or scan Git automatically.

Callers cannot supply or reuse a `freshness` field on a new review, and existing review history cannot be edited to add one. Stale Spec/Plan/snapshot reviews remain historical without a new content binding. Legacy final reviews missing bindings remain readable and return valid delivery HOLD, with `record-review` as the repair route after directly verifying the declared files. Do not rewrite historical evidence or initialize a replacement ledger.

## Resume a stopped task with a recorded claim

Generic `update` cannot change STOP_HOLD or PAUSED to another operating state, including changing STOP_HOLD to PAUSED. Record changed conditions and the existing human authority with a dedicated transaction:

```text
python scripts/task_ledger.py resume --ledger .task/ledger.json --input resume.json --expected-revision N --reason "record verified conditions for resuming"
```

```json
{
  "stop_ref": "r4",
  "prior_cause": "exact reason recorded when the task stopped",
  "changed_condition": "what changed so the recorded cause can be addressed",
  "evidence": "specific observation or saved result supporting the change",
  "authority": {"source": "actual user instruction reference checked by coordinator", "scope": "example-task"}
}
```

`stop_ref` identifies the original audit event entering the current uninterrupted stopped interval. Subsequent same-state budget, issue or review records do not replace that reference or cause; `prior_cause` must match its reason. For legacy history without recorded operating states, use `legacy:N`, where N is the last revision before the uninterrupted recorded stopped states (or the current revision if none records state), and explicitly supply the reconstructed prior cause from saved evidence. That legacy cause is caller-authored because the helper cannot recover an absent historical cause.

PAUSED additionally requires `"quota_ready": true` in the input. This records a claim, not quota telemetry. The coordinator must observe actual quota replenishment and actual user authorization before using the command; a generic continuation instruction is insufficient while quota remains at the user's pause threshold. STOP_HOLD may omit this field. Unknown fields, missing evidence, a wrong stop reference/cause, mismatched authority scope or stale CAS revision reject the write.

The transaction changes only the operating state to ACTIVE, increments the revision and appends the complete resume claim with the prior state to the audit. Counters, findings, reviews, reservations, original deadlines and earlier audit entries remain intact. Save failure preserves the stopped ledger. Resume supplies no approval, waiver, new allowance or external permission; remaining blockers still produce HOLD. The helper validates recorded claim structure and references only, and `authority_claims_verified` remains false.

## Repair legacy duplicate assignments

The earlier distinct-identity release rejected pre-existing gated ledgers whose core representatives shared an identity, preventing ordinary resume. Such structurally valid records can now be read and checked as HOLD; new `init` still refuses duplicate assignments. Normal updates cannot erase their responsibilities. Use the explicit narrow migration:

```text
python scripts/task_ledger.py repair-responsibilities --ledger .task/ledger.json --input corrected-reviewers.json --expected-revision N --reason "correct legacy duplicate assignments" --backup .task/ledger-before-repair.json
```

The input contains only `spec`, `plan`, `snapshot`, and `required_reviews`. Supply a fresh version/snapshot and the same role/scope responsibilities, correcting reviewer identities while retaining other assignment metadata. This command applies only when the old gated baseline has duplicate core identities and the new assignments are distinct. Other baseline fields, authority, counters, findings, reviews, transfers and old audit entries are retained. New current approvals are required; historical approvals are not copied. Effective transfer collisions can still keep the repaired record HOLD.

The helper checks CAS and transitions under the ledger lock, then creates the backup exclusively (never overwrites an existing path), preserves the exact original bytes, fsyncs it and atomically replaces the ledger. A save failure leaves the original ledger intact and may leave the completed backup; retry with a new backup filename and the still-current revision. The backup is protected from overwrite by this command, not an OS immutable file. Missing/corrupt schema or non-identity violations are not silently repaired. `authority_claims_verified` remains false.

## Verification policy and SOLO records

`baseline.verification` is `independent_final_qa` or `self_check`. Missing fields retain the original `independent_final_qa` behavior for existing ledgers. That policy requires current directly verified `FinalQA` evidence from outside the writer set, as before.

Choose `self_check` when initializing an ungated SOLO or directly verified task with no required review responsibilities and no applicable independent-review requirement. The helper accepts this policy only when `gated` is false and `required_reviews` is empty; it cannot authenticate whether the human or host actually required independence. Record the check through `record-review` with role `SelfCheck`, the current Spec/Plan/snapshot, scope, explicit verdict, nonempty evidence and `directly_verified: true`. The writer may supply this evidence. Current direct approval is required for every scope; stale, blind or latest current rejected checks leave delivery HOLD. Output reports `verification: self_check`, never independent QA. FinalQA entries cannot silently replace an absent SelfCheck record.

An independent policy, including the legacy missing-field default, cannot be downgraded on update. Self-check policy may be upgraded to independent QA with a fresh baseline version; old self-check evidence then cannot satisfy delivery. Required gates and review responsibilities remain monotonic. Choosing self-check cannot close an existing material issue: its issue-specific independent QA closure and originator confirmations still apply. Ledger records cannot supply authority to remove an external review requirement.

## Small updates without rewriting the ledger

Prefer these commands for routine records. Each reads the current ledger under its OS lock, applies only the requested change, and uses the same schema, transition, readiness and atomic-write checks as `update`. The caller supplies no audit or full candidate document. Every command requires `--expected-revision` and `--reason`; use the returned `revision` for the next operation. A stale revision is rejected without changing the file. The following commands are alternatives; replace `N` with the actual integer revision, not a shell variable.

```text
python scripts/task_ledger.py record-review --ledger .task/ledger.json --input review.json --expected-revision N --reason "record current QA evidence"
python scripts/task_ledger.py add-issue --ledger .task/ledger.json --input issue.json --expected-revision N --reason "record reproduced defect"
python scripts/task_ledger.py update-issue --ledger .task/ledger.json --input issue-change.json --expected-revision N --reason "record reassessment"
python scripts/task_ledger.py consume-budget --ledger .task/ledger.json --counter repairs --phase reserve --expected-revision N --reason "reserve next repair batch"
```

- `record-review` appends one complete review object using the schema below; IDs remain unique and past verdicts cannot be edited. Optional `verified_at` is accepted. Versions are explicit, never silently filled from the current baseline: a stale approval saves as historical evidence but cannot satisfy readiness.
- `add-issue` appends one issue object from the schema below, initially OPEN or CONTESTED. `closed_by` is supplied later through `update-issue`.
- `update-issue` accepts `{"id":"bug1","status":"RESOLVED","closed_by":"qa1"}`. Its optional `append_aliases` and `append_originators` arrays add attribution without replacing prior entries. Only these fields and `id` are accepted. Original severity, scope, closure criteria and statements remain unchanged. Recording RESOLVED does not supply missing independent QA, current evidence or originator confirmations; readiness stays HOLD until all obligations are met.
- `consume-budget` increments cumulative counters. `--counter` is `revisions`, `repairs`, `diagnostics`, `recovery_total`, `defects` or `recoveries`. The last two require a stable `--key`; other counters forbid it. Positive integer `--amount` defaults to 1. `--phase reserve` increases only reserved, `--phase use` only used, and `--phase both` (default) increases both. Use cannot exceed reservation. Reserve before dispatch, then record use; retain reservations on cancellation. A `recoveries` increment also increases `recovery_total` in the same transaction. Do not separately increment the total for that same attempt. A per-defect repair and its task-wide repair batch remain separate records because one batch may address several defects.

Unknown input fields and invalid payloads are rejected without a write. These convenience commands do not authenticate review claims or grant continuation: consumption beyond an allowance can be recorded, but the usual readiness HOLD still applies. For baseline changes, work-item ownership, transfers or continuation records, use the full-document `update`; narrow commands cannot rewrite these fields. Audit storage remains cumulative inside the ledger; these operations reduce caller reconstruction, not audit growth.

## Small schema

The initial document below deliberately has no approvals and therefore produces delivery HOLD. Replace the project root with the actual existing project directory.

```json
{
  "schema_version": 1,
  "task_id": "example-task",
  "project_root": "/path/to/existing/project",
  "operating_state": "ACTIVE",
  "baseline": {
    "level": "L2",
    "spec": "s1",
    "plan": "p1",
    "snapshot": "identified-stable-tree",
    "gated": false,
    "verification": "independent_final_qa",
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

- Required review: `{"role":"QA","reviewer":"qa-identity","scope":"all"}`. A gated scope also needs Architect and Developer entries, each represented by a different identity. Controlled transfer cannot merge these effective representatives into one person.
- Review: `{"id":"qa1","reviewer":"qa-identity","role":"FinalQA","scope":"all","spec":"s1","plan":"p1","snapshot":"identified-stable-tree","verdict":"APPROVED","evidence":"specific check/result reference","directly_verified":true,"issues":[]}`. Use `QA` for a plan approval, `FinalQA` for final integrated verification. Rejection uses `REJECTED`. Review IDs are unique; append subsequent verdicts instead of rewriting old ones. The latest applicable verdict controls each responsibility. QA and FinalQA must be outside the recorded writer set; their independence is conservatively task-wide. Architect and Developer may accept the design and later implement it. An original Developer finding may receive their own attributed confirmation after repair, but material closure additionally requires a current independent QA/FinalQA review listing the issue.
- Issue: `{"id":"bug1","aliases":[],"originators":[{"reviewer":"qa-identity","statement":"original failure and dissent"}],"scope":"all","severity":"MAJOR","status":"OPEN","closure_criteria":"specific repair evidence required"}`. Severity is BLOCKER, MAJOR, MINOR or SUGGESTION; status is OPEN, CONTESTED or RESOLVED. Resolution adds `closed_by` naming a current review explicitly listing this issue. Every original dissenter must directly confirm closure, or have a valid successor do so. An APPROVED summary without those confirmations cannot hide a material issue.
- Work item: `{"id":"work1","owner":"developer-identity","status":"ACTIVE","files":["src/example.py"]}`. Other statuses are PENDING, DONE and CANCELLED. Owners of files must be retained in `baseline.writers`. Ownership names explicit files, with one active work item per normalized path. Absolute paths, drive-relative paths, parent traversal, wildcard paths, directories and symlink escapes are rejected. Ownership checks do not acquire filesystem write locks; the coordinator must stop/await a writer before transfer.
- Counter maps `defects` and `recoveries` map stable defect/role-or-operation IDs to the same `{reserved,used}` shape. Both values are cumulative and never decrease; `used` cannot exceed `reserved`. Reserve before dispatch. Cancellation retains its reservation. The total recovery counters must cover all individual recovery counters. The helper cannot observe whether a dispatch was omitted from the record.

The task identity, root, level, writer attribution, existing scopes, required gate, independent-verification requirement and existing review responsibilities cannot be reset through updates. Reviews and transfers are append-only. Issues cannot be deleted, and original statements, aliases, severity, scope and closure criteria are preserved. Use a new issue for a distinct cause. A changed baseline requires a fresh Spec/Plan/snapshot tuple, and historical tuples cannot be reused to revive old approvals. A current explicit review entry can confirm applicability at the new tuple. The helper conservatively invalidates all tuple-bound approvals when that tuple changes; it does not infer cosmetic equivalence.

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

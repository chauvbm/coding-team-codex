# Bounded technical review

Read for full-team planning or material disagreement. Review should converge on a workable, testable solution.

## Review sequence

1. Freeze a concise scope and plan version. For full-team planning, Architect owns design; Developer checks feasibility; QA checks acceptance, failure modes and verification.
2. **R0:** reviewers independently inspect the same version. Do not give one reviewer's initial answer to another before their independent pass.
3. **R1:** consolidate findings with attribution. Address concrete correctness, security, integrity, compatibility and feasibility issues with the smallest justified revision.
4. **R2, only if needed:** reviewers check affected changes and unresolved issues. Stop repetitive debate when it produces no evidence; investigate, change approach or identify the decision needed.

These passes operate within the single task budget below. New defects stay recorded, but do not create more automatic allowance. A budget stop never resolves a defect or grants approval.

## Cumulative task budget and termination

Keep one Leader-owned ledger for the user task, with three separate cumulative allowances: Spec/Plan revision, investigation/retry, and implementation repair. Moving between activities cannot evade a stop or reset any counter. Defaults are conservative starting limits, not benchmark-derived optima.

| Activity | Automatic allowance per task |
| --- | --- |
| Initial review | One baseline review of Spec and one of its initial Plan, as needed; neither consumes a revision |
| Spec/Plan revision or reconsideration after a verdict | L0: no formal review required; L1: at most one cycle when needed; L2/L3: at most three shared cycles |
| Code repair plus verification | At most two attempts per underlying defect; at most four repair batches total across the task |
| Extra diagnosis of stalled debate/repair | At most one bounded diagnostic dispatch; only before a stopping limit is reached |
| Recovery from missing reviewers or failed investigation/review tools | One retry/replacement per required role or underlying failed tool operation; at most three recovery attempts shared task-wide |

Record the level before dispatch. Reclassification does not replenish an allocated budget. A user-requested formal team review on an otherwise L0 task uses the L1 allowance. L3's exceptional fourth Spec/Plan cycle requires explicit human authorization, an evidenced unresolved BLOCKER/MAJOR, a bounded new corrective proposal within scope, and verification criteria. Never autonomously dispatch it. Stop early once required approvals and acceptance are satisfied; unused capacity is not a reason to seek more objections.

Drafting the initial Spec/Plan is not a revision. Once the relevant document is submitted for its first formal review, correcting it in response to findings consumes a cycle, even if the first Plan has not yet been written. One coordinated Spec correction and dependent Plan update counts once. Freeze the affected Spec/Plan pair for that cycle; its first affected review is included, not a second charge. A fresh reconsideration request after a verdict consumes the next cycle even when neither document changes. Multiple reviewers in the same batch count once, not once per reviewer. Repeated review, baseline drafting or evidence gathering must not become an unmetered debate loop. Routine reads within a bounded assigned review are included; additional diagnosis/recovery uses the separate allowance below.

Before requesting a review, declare a finite total response deadline appropriate to expected runtime (default 180 seconds for a focused review). Polls and retries share that deadline; restarting an agent cannot extend it. A wait timeout alone is not necessarily an agent failure, but reaching the declared deadline or exhausting the permitted recovery allowance with no verdict ends automatic recovery. Stop/cancel outstanding work where supported, preserve output and leave the gate HOLD. Do not repeatedly start new waits after that stopping condition. A user-requested longer deadline can be recorded before dispatch.

Reserve a revision, repair, diagnostic or recovery attempt before dispatch, retain it after failure/cancellation, and count all agents working on the same requested correction as one coordinated batch. Parallel branches share the same task totals. Re-review of that correction is included in its cycle; repeatedly requesting reconsideration without a correction consumes the next cycle. Initial coding under a passed plan is not a repair attempt. A new defect consumes the same total repair budget; aliases and duplicate Issue IDs share the underlying defect's count.

Use a compact ledger with task ID, level, current Spec/Plan pair, used/reserved revision cycles, total repair batches and per-defect counts, extra diagnostic count, shared recovery count, per-role/per-operation retries and reviewer deadlines, gate and automatic state ACTIVE/PASS/STOP_HOLD. Include ledger state and remaining allowance in handoffs; preserve it across context compaction and reassigned agents. If history is unavailable, reconstruct it from saved evidence; do not assume zero and continue. If it cannot be reconstructed, stop the affected loop and report the missing history.

After the last permitted correction/repair returns, evaluate it: if acceptance/approvals are satisfied, PASS is allowed at the limit. Otherwise STOP_HOLD immediately. Do not dispatch a further diagnostic, correction or review merely because it would be read-only, a new approach or likely to work. Evidence of a new serious flaw still blocks the affected result; new evidence does not replenish allowance. Reopen resolved findings only for material new evidence, using the same ledger.

Plan version changes, new issue IDs, different models/agents, Leader takeover, R0 restarts, phase changes, context resets and splitting the same task into subtasks do not reset or extend limits. Tool retries count even if they return no useful evidence; retrying the same failure through another tool does not create a new allowance. No agent can replenish them. Resume beyond STOP_HOLD only on an explicit new human instruction to continue that affected work; preserve prior usage and record a finite added allowance (one affected cycle by default if the user gives no amount). Such continuation does not waive the gate, safety or scope requirements. Reviewer proposals, automated messages and unrelated user questions are not human continuation.

At STOP_HOLD, report unresolved findings and missing approvals, consumed budget, evidence and the smallest viable next step; terminate automatic dispatch for the stopped work instead of silently continuing another cycle. This is an operational termination outcome, not a claim the technical issue was solved or a requirement that the user decide a routine implementation detail.

## Findings and verdicts

For each material objection capture:
- A stable ID and originating reviewer.
- Requirement and plan version.
- Specific failure scenario, evidence and uncertainty.
- Severity, minimal corrective action and current resolution.

BLOCKER means a concrete critical failure or credible serious security/data-loss risk. MAJOR means a substantial correctness, compatibility or feasibility defect. MINOR and SUGGESTION do not block implementation unless their actual impact warrants reclassification with evidence.

Preserve original reviewer statements. Record Leader's disagreement separately; never rewrite a rejection as approval. Reviewers may update their own verdict after checking a fix. Reject out-of-scope preferences with a reason; do not silently implement them.

## Consensus and disagreement

Only report full-team consensus when Architect, Developer and QA explicitly accept the same current Spec/Plan pair and no material issue remains open or contested. Silence, an absent agent and Leader self-review are not consensus.

### Gate record and implementation handoff

When the Consensus Gate in SKILL.md applies, record:

```text
SPEC / PLAN: <current Spec version / Plan version and scope>
ARCHITECT: <Spec/Plan pair + design acceptance or pending>
DEVELOPER: <Spec/Plan pair + independent verdict or pending>
QA: <Spec/Plan pair + independent verdict or pending>
MATERIAL_ISSUES: <IDs + current state; none if resolved>
GATE: PASS | HOLD
REASON / NEXT_ACTION: <evidence or missing review>
```

PASS requires all current-pair approvals, no open or contested material issue, adequate acceptance tests and valid authorization. HOLD prohibits implementing the reviewed work even if the change is reversible or no reviewer has yet reported a defect. Diagnostic reproductions may continue only within remaining allowances before STOP_HOLD; unaffected independent work can continue. Only after PASS does Leader transfer write ownership.

Material changes to behavior, interfaces, persistence, scope or tests require an updated plan and renewed affected approvals. A material Spec change invalidates affected approvals even when the Plan text/version has not changed. Record renewed explicit acceptance of the current Spec/Plan pair; old Spec approvals cannot silently transfer. Use a concise requirement version label rather than requiring a separate Spec file for simple work. If a reviewer approves with notes but an unresolved MAJOR remains in the issue registry, request reconciliation; the summary label does not erase the issue.

An evidence-based rebuttal is not the origin reviewer's sign-off. Send the relevant evidence for a targeted reassessment; preserve dissent until that reviewer updates the finding/verdict. If a required reviewer cannot respond, keep HOLD and report the missing review. Do not manufacture approval or waive the gate automatically.

AUTO work does not require unanimous full-team consensus on every task. Leader can make reasoned technical decisions supported by evidence while accurately disclosing dissent. Do not proceed with an affected operation while a credible serious defect remains unresolved.

Ask the user when the disagreement requires a product, scope or authorization decision that cannot be resolved technically. User approval is separate from engineering review and is needed only when their instructions or the actual operation require it. Do not ask the user to adjudicate a routine implementation detail merely because reviewers disagree.

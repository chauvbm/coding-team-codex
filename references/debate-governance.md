# Bounded technical review

Read for multi-agent plan review or material disagreement. Leader routes issues; workers do not run an all-to-all debate. More execution capacity does not increase review-cycle allowances.

## Review sequence and issue routing

1. Freeze requirements, plan and review scope. For FULL_TEAM, name Architect, Developer and independent QA representatives. Additional workers report scoped findings rather than voting on every decision.
2. Initial reviewers independently inspect the same version. Do not share peers' conclusions before their first verdict. QA may derive acceptance cases from requirements before seeing the proposed solution when that would expose ambiguity.
3. Leader consolidates findings by underlying failure scenario. Send each disputed issue, relevant changes and evidence only to its owner and affected reviewer(s), usually two or three participants. Use a Specialist only for a distinct unanswered question. Agent count and majority votes never settle correctness.
4. Apply the smallest correction, then obtain affected reassessment. Initial review, correction and reassessment are phases, not an invitation to restart full-team rounds. Stop once acceptance and required approvals are satisfied.

## Canonical issues and evidence

Keep one registry for the task. Each issue records its canonical ID and aliases, all originators and original statements, requirement and reviewed Spec/Plan pair or code snapshot, affected scope/dependencies, failure scenario, evidence/uncertainty, severity, owner, closure criteria and status.

Merge duplicates only when they describe the same underlying failure and corrective action; similar symptoms from separate causes remain separate. Preserve every originator and dissent when merging. Duplicates share repair counts and one coordinated correction; eight reports of one bug are not eight repair batches.

BLOCKER is a concrete critical failure or credible serious security/data-loss risk. MAJOR is a substantial correctness, compatibility or feasibility defect. MINOR/SUGGESTION do not block unless their evidenced impact warrants reclassification. Leader records a rebuttal or proposed downgrade separately, without rewriting the originating reviewer's finding or rejection as approval. A summary APPROVED_WITH_NOTES cannot erase an open MAJOR in the registry.

Reopen a resolved issue only for material new evidence. Rephrasing an objection, adding votes, changing an agent/model, renaming an issue or restating a preference is not new evidence.

## Task ledger and default limits

Keep one cumulative Leader-owned ledger: task ID, level, Spec/Plan pair and scopes, task queue/dependencies and file owners, issue registry, used/reserved revision cycles, repair batches and per-defect counts, diagnostics, recovery attempts, reviewer deadlines, approvals, continuation authority, latest evidence/progress, gate and operating state. Preserve it across parallel branches, replacement agents, phase changes and context compaction. Reconstruct missing history from saved evidence; if impossible, hold the affected loop rather than assuming zero.

| Activity | Default task-wide allowance |
| --- | --- |
| Initial review | One requirements and one initial-plan baseline as needed; neither is a revision |
| Spec/Plan correction or reconsideration after a verdict | L0: no formal review; L1: one cycle; L2/L3: three cycles |
| Code repair and affected verification | Two attempts per underlying defect; four coordinated repair batches total |
| Extra diagnosis of a stalled issue | One bounded diagnostic dispatch, separate from routine reads in an assigned review |
| Missing-reviewer or failed-tool recovery | One retry/replacement per required role or underlying failed operation; three recovery attempts total |

Record level before dispatch. One coordinated requirements correction and dependent plan update counts once, even with several reviewers. Its first affected reassessment is included. Reconsidering a verdict without a correction still consumes the next revision. Initial implementation is not repair. Reserve counts before dispatch and retain them after failure/cancellation. No split, rename, reclassification or executor change resets counters.

Before a review, record a finite response deadline (normally 180 seconds for a focused review). Polls, retries and replacement share the original deadline; a timeout alone is not proof of failure, and a new agent does not extend it. Stop outstanding review/recovery at the deadline or recovery limit. Required missing acceptance remains HOLD; disclose the gap. Do not substitute Leader self-review or endlessly retry through another tool. A bounded replacement inspects current scope and inherited issues independently; it does not erase a former reviewer's dissent.

## Evidence workflow and termination

Track consecutive issue exchanges adding no material evidence or actionable correction. After two such exchanges, or at the applicable revision checkpoint, stop further argument-only exchanges. Leader records `EVIDENCE_MODE` and selects one concrete next action: a minimal reproduction, targeted source/test inspection, a bounded corrective change, or an actual product/permission decision. Record the hypothesis, evidence sought, owner, finite scope and success condition before dispatch. Keep participants scoped to the issue. This transition closes neither the issue nor a required gate.

Default revision/repair limits still terminate automatic continuation when no human authority extends them: evaluate the final allowed result, allow PASS if satisfied, otherwise record STOP_HOLD with findings and the smallest next step. There is no automatic fourth L2/L3 revision. A new human continuation can authorize a finite extension (one affected cycle when no amount is specified) or explicitly authorize continued necessary repair/verification.

When the human has already authorized autonomous necessary repair beyond these limits, record the source and scope of that authority. Treat the revision/repair numbers as checkpoints: continue an evidenced, bounded next repair or verification batch without asking again solely because a count was reached. Preserve all cumulative totals. After each batch, record the new observation, changed hypothesis/action and remaining defect; do not reopen general debate or claim an unlimited fresh budget. This exception does not automatically extend diagnostic/recovery allowances or reviewer deadlines, change eligibility, grant external permissions, waive approvals, or permit implementation under a required HOLD gate. A preimplementation correction here means revising the plan, not writing its gated implementation.

If the evidence action produces no usable evidence or actionable next step, or repeats the same failed approach without a changed testable hypothesis, stop that stalled loop in STOP_HOLD. Do not relabel another dispatch as verification to evade this stop. A diagnostic allowance/deadline or required-review recovery exhausted unresolved also stops its loop. Record the concrete blocker and continue unaffected authorized work; resume only with the missing evidence, external change or applicable explicit authorization. Ask the user only when an actual product, scope or permission decision is required, not to adjudicate a routine technical detail. A switch to a materially different evidence-backed approach must be recorded, not invented to reset limits.

Honor any explicit user quota-pause threshold when trustworthy remaining-usage information is available. Pause work, stop/await workers safely, and preserve the ledger until replenished. Do not infer a percentage from token counts or claim unavailable quota telemetry.

## Consensus Gate and scoped approvals

For FULL_TEAM, a selected full-team plan review or a user-required gate, record:

```text
SPEC / PLAN / SCOPE: <current pair and affected scope>
ARCHITECT: <named representative, scope, version, design acceptance or pending>
DEVELOPER: <named representative, scope, version, independent verdict or pending>
QA: <named independent representative, scope, version, verdict or pending>
OTHER_AFFECTED_REVIEWS: <required specialist/owner verdicts, if applicable>
MATERIAL_ISSUES: <canonical IDs and current states>
GATE: PASS | HOLD
OPERATING_STATE: ACTIVE | EVIDENCE_MODE | STOP_HOLD | PASS
CONTINUATION: <default allowance or actual human authority, with source/scope>
NEXT_ACTION: <evidence, owner and success condition, or blocker>
```

PASS requires explicit current applicable approvals from the three representatives and any required scoped reviewers, no open/contested material issue from any worker, testable acceptance and valid authorization. Silence, vote totals, a replacement agent, Leader rebuttal or a closed discussion do not supply acceptance. Under a required gate the originating reviewer must explicitly reassess their contested finding; if that acceptance is unavailable, keep HOLD and report it. Transfer implementation ownership only after PASS.

Material changes to behavior, interfaces, persistence, requirements, scope or acceptance tests invalidate affected approvals and dependent conclusions. Obtain explicit affected reassessment of the new pair. An unchanged reviewer may carry acceptance forward only through an explicit applicability confirmation for the new pair/scope; Leader cannot silently copy it. Cosmetic edits can retain approval with a recorded no-impact rationale. A version label alone does not require every worker to repeat the entire review. Keep covered implementation HOLD while affected approval is missing; unaffected authorized work can proceed.

Ordinary AUTO work has no universal unanimity requirement. Leader can resolve nonmaterial disagreements with evidence and preserve dissent accurately; credible unresolved serious defects still block affected delivery. Plan consensus never replaces independent review and meaningful checks of the final stable integrated changes.

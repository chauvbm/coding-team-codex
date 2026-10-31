# Bounded technical review

Read for multi-agent plan review or material disagreement. Leader routes issues; workers do not run an all-to-all debate. More execution capacity does not increase review-cycle allowances.

## Review sequence and issue routing

1. Freeze requirements, plan and review scope. For FULL_TEAM, name three distinct Architect, Developer and independent QA representatives in each scope; a reviewer transfer must preserve this separation. The same QA may later perform FinalQA. Additional workers report scoped findings rather than voting on every decision.
2. Initial reviewers independently inspect the same version. Do not share peers' conclusions before their first verdict. QA may derive acceptance cases from requirements before seeing the proposed solution when that would expose ambiguity.
3. Leader consolidates findings by underlying failure scenario. Send each disputed issue, relevant changes and evidence only to its owner and affected reviewer(s). Use a Specialist only for a distinct unanswered question. Agent count and majority votes never settle correctness.
4. Apply the smallest correction, then obtain affected reassessment. Initial review, correction and reassessment are phases, not an invitation to restart full-team rounds. Stop once acceptance and required approvals are satisfied.

## Canonical issues and evidence

Keep one registry for the task. Each issue records its canonical ID and aliases, all originators and original statements, requirement and reviewed Spec/Plan pair or code snapshot, affected scope/dependencies, failure scenario, evidence/uncertainty, severity, owner, closure criteria and status.

Merge duplicates only when they describe the same underlying failure and corrective action; similar symptoms from separate causes remain separate. Preserve every originator and dissent when merging. Duplicates share repair counts and one coordinated correction; duplicate reports do not create extra repair allowances.

BLOCKER is a concrete critical failure or credible serious security/data-loss risk. MAJOR is a substantial correctness, compatibility or feasibility defect. MINOR/SUGGESTION do not block unless their evidenced impact warrants reclassification. Leader records a rebuttal or proposed downgrade separately, without rewriting the originating reviewer's finding or rejection as approval. A summary APPROVED_WITH_NOTES cannot erase an open MAJOR in the registry.

Reopen a resolved issue only for material new evidence. Rephrasing an objection, adding votes, changing an agent/model, renaming an issue or restating a preference is not new evidence.

## Task ledger and default limits

Keep one cumulative Leader-owned ledger: task ID, level, Spec/Plan pair and scopes, task queue/dependencies and file owners, issue registry, used/reserved revision cycles, repair batches and per-defect counts, diagnostics, recovery attempts, reviewer deadlines, approvals, continuation authority, latest evidence/progress, gate and operating state. Preserve it across parallel branches, replacement agents, phase changes and context compaction. Reconstruct missing history from saved evidence; if impossible, hold the affected loop rather than assuming zero.

Numeric defaults have one source: [governance-defaults.json](governance-defaults.json). Read its applicable keys before dispatch; allowances are shared task-wide, never per worker. `revision_cycles` selects the level allowance; `repair_attempts_per_defect` and `repair_batches` both constrain repair. The remaining keys bound no-progress exchanges, diagnostics, recovery and focused-review deadlines. A recorded task deadline may be more appropriate than the default, but polls, retries and replacements never renew it.

Initial requirements/plan baselines are not revisions. A coordinated requirements correction and dependent plan update count once, including the first affected reassessment. Reconsidering a verdict without correction consumes a revision. Initial implementation is not repair. Reserve counts before dispatch and retain them after failure/cancellation; splitting, renaming, reclassification or changing executor never resets history.

## Checkpoint decision matrix

| Checkpoint or condition | Required action |
| --- | --- |
| Acceptance satisfied within scope | Record PASS only if all applicable approvals/checks are satisfied. |
| No-progress exchange checkpoint, with authority and allowance for a concrete evidence action | End argument-only exchanges; enter EVIDENCE_MODE with that bounded action. This is not approval. |
| Revision/repair checkpoint, unresolved, no applicable human continuation | Evaluate the final allowed result, then STOP_HOLD that loop; record findings and smallest next step. |
| Revision/repair checkpoint, applicable explicit human continuation | Record source/scope and an evidenced next batch; preserve totals. Do not ask again solely for the count. |
| Evidence action yields no usable evidence/action, or repeats a failed approach without a changed testable hypothesis | STOP_HOLD the stalled loop; do not rename another dispatch as verification. |
| Diagnostic allowance/deadline or reviewer/tool recovery exhausted unresolved | STOP_HOLD that loop; preserve missing acceptance and report the blocker. |
| Required gate lacks current approval or has a material contested finding | HOLD covered implementation; continue only authorized investigation, plan repair or unaffected work. |
| Explicit quota-pause threshold reached using trustworthy telemetry | Pause safely and preserve ledger until replenished; do not infer percentages from token counts. |

Apply pause and exhausted-allowance stops before starting an evidence action. Gate status is a separate constraint: an allowed evidence/plan-repair step never permits covered implementation while the gate is HOLD. At a revision checkpoint, the applicable continuation row decides whether another action is allowed.

A new human continuation may authorize a finite extension (the next affected cycle if no amount is specified) or expressly authorize continued necessary repair/verification. Such authority changes revision/repair checkpoints only: it does not extend no-progress, diagnostic, recovery or deadline limits, change eligibility, grant external permissions or waive gates. Reviewer/tool messages and ON do not supply it. Preimplementation repair means revising the plan, not writing gated implementation.

### Evidence and recovery procedure

Track consecutive exchanges without material evidence or actionable correction using `no_progress_exchanges`. In EVIDENCE_MODE record a hypothesis, evidence sought, owner, finite scope and success condition before dispatch. Choose a minimal reproduction, targeted source/test inspection, bounded correction, or actual product/permission decision. After each batch record observation, changed hypothesis/action and remaining defect; do not restart general debate or claim a fresh budget.

Extra stalled-issue diagnosis uses `diagnostic_dispatches`; routine reads within an assigned review do not. Reserve recovery before retry/replacement against both `recovery_per_role_or_operation` and `recovery_total`; changing tools does not reset the failed operation. Record the finite original review deadline before dispatch using `review_deadline_seconds` as the focused-review default. A timeout alone is not proof of failure. At deadline or recovery exhaustion, stop outstanding review/recovery; required missing acceptance stays HOLD. Leader self-review cannot replace it. A bounded replacement independently inspects current scope and inherited issues without erasing former dissent.

STOP_HOLD applies to the concrete loop, not unaffected authorized work. Resume only on missing evidence, external change or applicable explicit authority addressing its stopping reason. Record a materially different evidence-backed approach; never invent one to reset limits. Ask only for actual product, scope or permission decisions. Quota pause honors task-specific human instructions only when reliable telemetry exists; never claim unavailable telemetry.

At STOP_HOLD, report the blocker and smallest next step. Do not ask for a speculative renewal merely because an automatic allowance or deadline expired; ask only when completing the requested task actually requires a concrete user decision or authorization.

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

PASS requires explicit current applicable approvals from the three representatives and any required scoped reviewers, no open/contested material issue from any worker, testable acceptance and valid authorization. Silence, vote totals, a replacement agent, Leader rebuttal or a closed discussion do not supply acceptance. The originating reviewer normally reassesses their contested finding; when unavailable, only the controlled transfer below can assign that responsibility to a successor. Missing applicable acceptance keeps HOLD. Transfer implementation ownership only after PASS.

### Controlled reviewer transfer

Transfer a required review only when the original reviewer is unavailable, cancelled or has reached a recorded bounded response timeout. A timeout does not prove the finding wrong or renew the review deadline. Before transfer, record the reason and source of unavailability, old/new reviewer IDs, affected scopes and canonical issues, current version/snapshot, closure criteria, original rejection/evidence and attribution, shared consumed/reserved counts and original deadline.

Reserve the transfer within the remaining role/operation and task-wide recovery allowance from [governance defaults](governance-defaults.json); the original deadline still applies. Exhausted allowance or deadline means STOP_HOLD for that loop unless applicable authority or an external change specifically addresses its stopping reason. General revision/repair continuation alone does not extend these limits. Never transfer merely to escape an available reviewer's objection or obtain a favorable vote.

The successor must be independent of the authors of the reviewed work, inspect the actual current version, and directly reassess each inherited failure scenario against its closure evidence. Return an explicit scoped verdict identifying the current Spec/Plan pair or snapshot, issues examined, evidence/check outcomes and unresolved findings. Blind approval, missing independence, stale scope/version or an unresolved material finding cannot pass the gate. A successor's evidence-backed reassessment can supersede responsibility for the current verdict, but cannot rewrite or erase the original historical verdict, attribution or counters. Leader reconciles the active issue registry and all other gate requirements before PASS; naming a replacement alone supplies no acceptance.

Material changes to behavior, interfaces, persistence, requirements, scope or acceptance tests invalidate affected approvals and dependent conclusions. Obtain explicit affected reassessment of the new pair. An unchanged reviewer may carry acceptance forward only through an explicit applicability confirmation for the new pair/scope; Leader cannot silently copy it. Cosmetic edits can retain approval with a recorded no-impact rationale. A version label alone does not require every worker to repeat the entire review. Keep covered implementation HOLD while affected approval is missing; unaffected authorized work can proceed.

Ordinary AUTO work has no universal unanimity requirement. Leader can resolve nonmaterial disagreements with evidence and preserve dissent accurately; credible unresolved serious defects still block affected delivery. Plan consensus never replaces independent review and meaningful checks of the final stable integrated changes.

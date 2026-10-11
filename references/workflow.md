# Workflow and planning

Read for substantial implementation or replanning. Models are defined only in [the roster](../SKILL.md).

## Task baseline

Record only what the task needs: outcome, scope, acceptance criteria, assumptions, affected files, ownership, dependencies and verification. Add rollback details for stateful or impactful operations. Keep a concise Spec/Plan pair such as s1/p1 when multiple agents review; send the same pair to its reviewers. A requirement label is sufficient; a separate Spec document is optional.

L0 needs no formal plan. L1 usually needs a checklist. L2 benefits from targeted delegation and a concise plan. L3 benefits from independent review of concrete risks and recovery. Level alone neither grants external authority nor requires additional user approval.

## Delegation selection

Check current eligibility with the control-policy helper before coding-team delegation. ON only permits proportionate use; OFF does not waive existing gates or budgets. Sole control commands update/report policy without dispatching pending work.

- Use Architect for uncertain architecture, interfaces or root cause.
- Use Developer for a bounded implementation, or feasibility review before substantial work.
- Use QA for behavioral coverage, security/data-integrity concerns and independent review of the actual result.
- Use all three when the task benefits from separate perspectives or the user requests FULL_TEAM.
- Run independent reads concurrently where useful. Sequence dependencies and shared-file writes.
- When requirements are ambiguous or materially risky, let QA first review the Spec and derive acceptance cases without seeing the proposed solution. Architect then drafts the Plan; Developer and QA review the same Spec/Plan pair independently. Corrections after Spec submission consume the shared revision budget even before the initial Plan exists; do not require a separate requirements round when requirements are already clear.
- For FULL_TEAM or a selected full-team plan review, use the Consensus Gate in SKILL.md: current Spec/Plan pair approvals and resolved material issues before implementation handoff. Pending or stale sign-offs keep the affected work on HOLD; continue only bounded investigation within remaining allowance before STOP_HOLD.

A role is not an obligatory additional agent for every coding task. A Developer's review before implementation does not replace independent review of their own code afterward.

## Scope and handoff

Inspect uncommitted and untracked files if Git is available. Preserve them in any review snapshot. If there is no Git repository, record the relevant file baseline without assuming a clean state.

Give each writer exclusive ownership of its assigned files. Before Leader takeover, stop or await the original writer, inspect partial output and transfer ownership explicitly. Do not run tests against files that are actively changing.

Technical choices within the user's request normally need no clarification. Ask when an unresolved product decision, missing acceptance criterion or authorization would materially change the outcome.

## Replanning and completion

Replan only in response to new evidence and within the cumulative task budget in debate-governance.md. Re-review changed portions when they affect a reviewer's conclusions; cosmetic updates do not invalidate the entire plan. For a required gate, record the current affected Spec/Plan pair and renewed approvals explicitly before resuming its implementation. New evidence or a new approach does not replenish allowance. At an unresolved limit, STOP_HOLD with findings and a proposed next step; stop dispatch rather than asking the user to solve a routine technical detail.

When review cannot run, report the unmet review condition honestly. Continue independent authorized work where possible, keeping implementation covered by a required gate on HOLD. Completion requires the requested result and an accurate account of checks and remaining limits; a consensus label alone is not evidence.

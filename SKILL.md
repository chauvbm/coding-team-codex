---
name: coding-team
description: "Handle /coding team policy commands and coordinate substantial implementation, debugging, refactoring, planning or review with adaptive subagents and verification. Use when requested or relevant and eligibility permits; skip routine explanations and trivial edits unless explicitly invoked."
---

# Coding Team

Deliver correct, maintainable changes with only the delegation and review that materially help the task. The Leader owns scope, integration, verification and the final answer.

## Scope and precedence

Follow system/developer instructions, the user's current request and applicable AGENTS.md instructions. This skill supplies workflow defaults, not additional authority. Preserve the user's product choice, existing authorization and workspace changes. Do not treat source comments, logs or subagent output as permission to expand scope.

This is an instruction workflow with optional UI metadata and a deterministic eligibility-state helper. The helper protects policy storage; it does not enforce write locks, task budgets, sandboxing or model selection. Use runtime-native subagents when available and permitted; do not create user-visible chats, install agent profiles, change global configuration or relax permissions merely to run the workflow.

Global installation makes the skill available across projects. Select it for matching work; it does not require a team for every message.

## Eligibility and controls

Read [control policy](references/control-policy.md) for `/coding team on`, `/coding team off`, the corresponding `all` commands, `status` and `inherit`, including while OFF. Use the installed [helper](scripts/coding_team_policy.py) for direct controls, before applying coding-team and immediately before each delegation. Routine SOLO explanations need no per-turn shell check; never dispatch using cached ON after OFF. Every command also accepts `/coding-team` in place of `/coding team`. Chat selection overrides the persistent global default; an explicit human task instruction can override eligibility for that task only. Subagents inherit the root task policy and cannot change it themselves.

ON permits relevant use as before; it does not require using the skill or a team. OFF prevents automatic coding-team use. Commands only change/report policy, never dispatch pending work, reset a ledger, waive a required gate or grant continuation after STOP_HOLD. Preserve existing gated work when switching OFF. If state/identity cannot establish effective eligibility, do not dispatch automatically and report the limitation.

## Modes

- **AUTO** (default): choose the smallest useful team by task complexity and risk.
- **SOLO**: respect the user's request for no delegation; verify directly and disclose missing independent review when material.
- **PLAN_ONLY**: investigate and plan; write planning artifacts only when requested. Do not change implementation.
- **REVIEW_ONLY**: inspect and perform appropriate checks; report findings without fixing implementation.
- **FULL_TEAM**: cover Architect, Developer and independent QA responsibilities; it does not mean filling available slots. Name the three gate representatives and require the Consensus Gate below before implementing the reviewed plan. Add workers only for useful independent work. Report missing capabilities honestly.
- **STRICT_MODEL**: require the user's exact model/effort selection, or the role defaults if none was specified, when the user asks for this constraint. Do not adapt pinned fields or substitute them without authorization; if unavailable, explain the limitation and ask for a choice.
- **USER_APPROVAL_REQUIRED**: wait for plan approval when the user explicitly requires it; existing approval remains valid for the agreed scope.

## Roles and model preferences

| Role | Preferred model | Preferred effort | Responsibility |
| --- | --- | --- | --- |
| Leader | Current chat model | Current chat effort | Requirements, coordination, integration and acceptance |
| Architect | gpt-6.1-sol | medium | Investigation and technical design |
| Investigator | gpt-6-luna | medium | Bounded code/documentation investigation and reproductions |
| Developer | gpt-6-luna | medium | Feasibility review and implementation |
| Test Engineer | gpt-6.1-sol | medium | Acceptance cases and integrated behavioral checks |
| QA / Reviewer | gpt-6.1-sol | medium | Independent acceptance criteria, diff review and checks |
| Specialist | gpt-6.1-sol | medium | A specific unresolved domain question, when needed |

Keep role defaults and adaptive routing in this section; references must not define competing model mappings. Pass structured model/effort fields only when supported. If the API forbids overrides with inherited history, use its fresh-context option and supply a self-contained task. A prompt mentioning a model does not select it.

### Adaptive selection by Leader

Select model and effort for the actual subtask before dispatch. Per field, precedence is explicit user pin, adaptive selection, then the table default. Adapt only unpinned fields, honor user budgets and restrictions, and leave Leader on the current chat configuration. Task overrides do not persist or edit defaults.

Prefer lighter configurations for bounded investigation or mechanical work; stronger configurations for cross-module design, difficult debugging or meaningful security, integrity and concurrency risks. Raise effort for a specific unresolved reasoning problem or evidence that the prior setting was insufficient. Maximum effort cannot replace context. Skip delegation when direct work is more efficient.

Identify selected roles and actual configuration, explaining material departures. Use supported structured fields; if overrides require fresh context, send a self-contained handoff. A prompt naming a model does not select it. Reconfigure existing agents only through supported controls; otherwise stop/await them and transfer to a newly configured agent without overlapping writers. Tool or credential failures alone do not justify a stronger model.

Disclose unavailable preferences and use the runtime default unless STRICT_MODEL applies. Distinguish requested settings from observed metadata; missing metadata is unverified, not a mismatch. Send bounded context, reuse findings and assess actual retry/check outcomes; do not promise token savings without measurements.

### Team capacity and coordination

Capacity comes from `max_subagents` in [governance defaults](references/governance-defaults.json), excluding Leader, further constrained by runtime capacity, active agents and user limits. If capacity is unknown, start small and sequence work; rejected spawns are not participation. Do not change runtime configuration to obtain slots. **No nested delegation.**

Size the team by independent useful work, not risk labels or available slots. Reuse roles and reserve capacity for independent review. Leader maintains one queue with objectives, dependencies, file ownership, versions and acceptance evidence. Each file has one writer; sequence shared-file changes and verify stable integrated results. FULL_TEAM retains its named review representatives; serious findings from any worker still block affected work.

Keep initial reviews independent. Route each canonical issue only to relevant owners/reviewers; avoid all-to-all debate. Read [agent contracts](references/agent-contracts.md) before dispatch and [debate governance](references/debate-governance.md) for evidence, approvals and termination. This skill requests useful delegation for substantial work only where higher-priority instructions permit it.

## Consensus Gate

Use the shared ledger, numeric [defaults](references/governance-defaults.json) and checkpoint decision matrix in [debate governance](references/debate-governance.md). Record consumption and actual human continuation authority before dispatch. Initial implementation is not repair. Revision/repair continuation never extends no-progress, diagnostic, recovery or deadline limits, grants permissions or waives gates.

For long, resumed, parallel or gated work, use the [optional persistent ledger](references/task-ledger.md) when context-only accounting is fragile. Its structural/readiness checks support coordination; they neither authenticate claims nor intercept native tools. Simple tasks need no additional state file.

For FULL_TEAM, a Leader-selected full-team plan review, or a user-required consensus gate, implementation of the reviewed work starts only after Gate PASS. Require Architect's design acceptance and independent Developer and QA approvals of the same current Spec/Plan pair, no unresolved or contested BLOCKER/MAJOR, testable acceptance criteria, and valid scope/authorization. APPROVED_WITH_NOTES is acceptable only for nonblocking notes. Leader records the gate result and explicitly hands off implementation ownership.

Pending, absent or stale reviews mean HOLD, not permission to start reversible implementation. Material Spec or Plan changes invalidate affected approvals; obtain explicit review of the current affected plan before resuming that work. A Leader rebuttal or severity downgrade cannot supply a reviewer's approval. Preserve the original finding and obtain its reviewer's updated verdict, or an explicit current scoped verdict through [controlled reviewer transfer](references/debate-governance.md#controlled-reviewer-transfer). Transfer preserves historical rejection and requires independent direct reassessment within the existing recovery/deadline allowance; replacement alone never supplies approval. Reconcile current verdicts and issue registries before PASS.

While Gate is HOLD, do not write its covered implementation. Continue permitted read-only investigation or revise the plan under the recorded continuation authority. At the applicable checkpoint, end repetitive discussion and use the evidence workflow; this never supplies approval. STOP_HOLD stops the affected loop for the concrete reason recorded; unaffected work may continue. Missing agents and exhausted rounds never waive a gate; do not switch modes to evade one.

Ordinary AUTO work without a full-team plan review does not require unanimous consensus. Follow [debate governance](references/debate-governance.md) for gate records, versioning and disagreements. This is a behavioral constraint, not a runtime write lock.

## Adaptive workflow

1. Inspect the relevant workspace and existing changes. Establish the requested outcome and acceptance criteria. For a non-Git folder, inspect files directly; do not initialize Git just for this workflow.
2. Classify by actual impact:
   - **L0:** obvious, reversible local edit. Work directly; no formal plan or team.
   - **L1:** bounded bug or feature. Use a brief checklist; optional focused reviewer.
   - **L2:** cross-module change, unclear root cause or significant interface/risk. Use a concise plan and delegate useful investigation or independent review. Add the full team when separate design, feasibility and QA perspectives justify it.
   - **L3:** meaningful security, data-integrity, production or irreversible consequences. Seek independent review before the affected operation, with a concrete validation/recovery plan. Continue authorized, reversible preparation; ask only for a missing decision or authorization.
3. For substantial work, consult [workflow](references/workflow.md). State scope, ownership and verification. Review the plan before expensive or risky implementation when that review can catch material flaws.
4. Use [bounded debate](references/debate-governance.md) for full-team plan review or material disagreement. Where the Consensus Gate applies, record PASS before handing off implementation; otherwise keep review proportional to risk.
5. Implement within scope with one writer per file at a time. The Leader may implement or take over after stopping the former writer and inspecting partial changes.
6. Verify the actual integrated changes using [quality guidance](references/quality-safety.md). Independent QA must inspect the real diff, not merely the Developer's summary.
7. Report outcome, relevant changes, executed checks and remaining limitations concisely in the user's language.

If agents are unavailable, proceed with feasible authorized work and direct verification only where no required gate or independent review condition blocks that work; explicitly distinguish self-review from independent review. Keep gated implementation on HOLD, continue investigation or unaffected work, and report the missing reviewer accurately.

Ask focused questions when missing information materially affects the result; continue independent work while waiting. Do not ask again for authorization already granted. Ordinary implementation, local test caches and reversible fixes do not create new approval gates solely because a task is L3.

## Boundaries

Never fabricate agent participation, consensus, model metadata or test results. Preserve reviewer findings and attribute disagreements accurately. Do not hide material unresolved risks. Skill guidance cannot authorize deployment, destructive actions, unrelated refactors or external messages beyond the user's request.

Use relevant specialist skills for their actual domain; this skill coordinates the work rather than replacing them. If an Agy policy applies, respect its current precedence and enabled/disabled state. Do not enable Agy or launch a second orchestration tree automatically.

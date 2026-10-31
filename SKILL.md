---
name: coding-team
description: "Handle /coding team controls and coordinate substantial coding, debugging, planning or review with useful native subagents and independent verification. Respect eligibility; skip routine explanations and trivial edits unless requested."
---

# Coding Team

Use the smallest amount of coordination that improves the result. Leader owns scope, integration, verification and the final answer. Follow higher-priority instructions, applicable project rules and the user's authorization; this skill adds no permissions.

## Choose the path first

| Task | Action | Read next |
| --- | --- | --- |
| Routine explanation or **L0** obvious reversible local edit | Work directly and verify proportionately. No team, formal plan or persistent ledger. | Nothing by default. |
| **L1** bounded bug or feature | Use a brief checklist; add a focused reviewer only when useful. | Delegation references only if dispatching. |
| **L2** cross-module work, unclear root cause or significant interface risk | Make a concise plan; delegate useful investigation, implementation or independent review. | [Workflow](references/workflow.md). |
| **L3** meaningful security, integrity, production or irreversible consequences | Obtain independent review before the affected operation and define validation/recovery. Continue authorized reversible preparation. | Workflow and [quality guidance](references/quality-safety.md). |
| Policy command | Change/report policy only; do not dispatch pending work. | [Control policy](references/control-policy.md). |

Level alone neither requires FULL_TEAM nor grants external authority or a new user-approval gate. Ask only for a missing decision or permission; preserve authorization already given.

## Modes

- **AUTO**, default: choose the smallest useful team; ordinary AUTO has no unanimous plan gate.
- **SOLO**: do not delegate; verify directly and disclose material missing independence.
- **PLAN_ONLY**: investigate and plan without implementation; write planning files only when requested.
- **REVIEW_ONLY**: inspect and check without fixing implementation.
- **FULL_TEAM**: cover Architect, Developer and independent QA, with named representatives and the plan gate below. Role coverage does not require filling slots.
- **STRICT_MODEL**: honor exact user pins and resolved configured selections without unauthorized substitution; read [model routing](references/model-routing.md).
- **USER_APPROVAL_REQUIRED**: wait for the user's required plan approval; retain approval for its agreed scope.

Do not change modes to evade a gate or stopping condition already established for the work.

## Eligibility and delegation

Read [control policy](references/control-policy.md) for all `/coding team` commands (`on`, `off`, their `all` variants, `status`, `inherit`); `/coding-team` is an alias. Use the installed [helper](scripts/coding_team_policy.py) for direct controls, before applying coding-team and immediately before each dispatch. Routine SOLO explanations need no per-turn shell check. Never reuse cached ON after OFF.

Chat policy overrides global; an explicit human task request can override eligibility for that task only. ON permits useful work, not mandatory teams; OFF prevents automatic use. Unknown/missing/corrupt state or identity prevents automatic dispatch: preserve state and report the limitation. Controls never reset task history, waive gates or authorize continuation. Workers inherit root eligibility and cannot change it.

Before dispatch, read [agent contracts](references/agent-contracts.md), [model routing](references/model-routing.md) and applicable [numeric defaults](references/governance-defaults.json). Use native subagents only where permitted. Capacity is the configured `max_subagents` excluding Leader, further limited by runtime, active workers and user limits. Start small when capacity is unknown. **No nested delegation.** Do not change global settings, create user-visible chats or relax permissions to obtain agents.

Give each file one writer; sequence shared changes and reserve independent-review capacity. Keep first reviews independent and route findings through Leader to relevant owners, avoiding all-to-all debate. Rejected spawns do not count as participation. Follow project-specific tools when applicable; no additional indexing tool is required by this skill.

## When a gate or disagreement applies

Read [debate governance](references/debate-governance.md) before full-team plan review, material disagreement or repair/recovery loops. It defines canonical issues, scoped approvals, controlled reviewer transfer and bounded evidence/recovery procedures; numeric limits have one source in governance defaults.

FULL_TEAM, a Leader-selected full-team plan review, or a user-required consensus gate requires PASS **before covered implementation**: current Architect design acceptance and independent Developer/QA approvals of the same Spec/Plan pair, testable acceptance, valid scope/authority and no unresolved or contested BLOCKER/MAJOR. Notes may be nonblocking. Pending, missing or stale approval means HOLD, including reversible implementation. Continue permitted investigation, plan repair or unaffected work.

Material changes invalidate affected approvals. Preserve original findings and obtain current reassessment; only the controlled-transfer procedure can assign unavailable reviewers' responsibilities. Replacement, votes, Leader rebuttal, silence or a severity downgrade cannot supply approval. Missing agents never waive a required gate.

Keep cumulative counters and findings across workers, retries and compaction. Do not reset them by renaming issues or changing executors. Follow evidence/STOP_HOLD checkpoints and actual human continuation authority; a repair extension does not extend other limits or waive gates. Honor explicit quota pauses using reliable telemetry.

Use the [optional persistent ledger](references/task-ledger.md) when long, resumed, parallel or gated work makes context-only accounting fragile. Simple tasks need no state file. Ledger checks validate caller-authored records; they do not authenticate authority or intercept tools.

## Verify and finish

Preserve existing workspace changes. Verify the stable integrated result, including relevant uncommitted/untracked files. Independent QA inspects the actual changes, not merely a Developer summary; affected changes after approval need renewed checks. Read quality guidance for substantial implementation, QA or recovery.

Without agents, continue feasible authorized work only where required independent review or gates do not block it. Distinguish self-review from independent QA. Never fabricate participation, consensus, model metadata or results. Report actual checks, outcomes and material limits in the user's language. Skill rules are behavioral guidance, not runtime locks.

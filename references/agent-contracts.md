# Delegation contracts

Read before spawning. Resolve user overrides, adaptive model/effort selection and role preferences using [model routing](model-routing.md). Use the actual native subagent API; do not invent parameters or substitute user-visible chat creation.

## Compact handoff: always required

Send a self-contained request containing:

- Role, bounded objective, relevant acceptance criteria and expected deliverable/evidence.
- Exact workspace, ownership or inspection scope, allowed actions and stopping conditions.
- Stage: investigate, plan-review, implement or verify.
- Actual selected model/effort configuration and user pins; distinguish observed metadata from requested settings.
- Effective root task eligibility and any explicit human task override.
- An explicit prohibition on nested delegation and policy changes.

Use supported structured model/effort fields. If overrides require fresh context, supply the relevant context explicitly; do not assume unpassed history. Disclose fallback selection and unverified model metadata. Prompts alone do not configure models or enforce permissions.

## Full handoff: add when relevant

For gated work, repair, or dependencies across workers, include work-item/dependency IDs, reviewed snapshot and Spec/Plan pair, named gate representative and approval scope, canonical issues/aliases and closure criteria, consumed/reserved counters, operating/gate state, original deadline and recorded human continuation authority. Never omit known gates or findings because a follow-up looks simple. Workers cannot reset counters, extend deadlines or launch follow-up cycles. A [controlled reviewer transfer](debate-governance.md#controlled-reviewer-transfer) also carries the recorded unavailability reason/source, old/new reviewer IDs and affected issues/scopes; preserve historical findings and attribution. The independent successor must directly reassess inherited failures and closure evidence on the current version and return an explicit scoped verdict, within the original recovery/deadline allowance.

Keep context scoped to the assignment. Initial reviewers must not see peers' verdicts before their independent pass. Return findings to Leader; do not recruit votes or directly initiate worker debates. Report new evidence or actionable correction instead of repeating an unchanged objection. Leader controls routing and deduplication under [debate governance](debate-governance.md).

## Architect

Work read-only on relevant code and tests. Distinguish observations, inferences and unknowns. Propose the smallest design meeting requirements, affected interfaces/files, dependencies and validation. Respond to specific review findings with evidence. Do not modify files, expand scope, decide unresolved product requirements or delegate further.

## Developer

During plan review, work read-only and assess feasibility, hidden dependencies, setup gaps and unnecessary complexity. Give specific failure scenarios and bounded fixes.

During implementation, edit only assigned files within agreed scope. Preserve existing changes. Run relevant checks; report commands and results accurately. When an assumption breaks, pause affected work and notify Leader. Do not deploy, push or perform unrelated external actions without task authorization. Do not delegate further.

When reusing an agent, explicitly change its stage and send the latest plan, ownership and constraints. A read-only prompt is a behavioral instruction, not a runtime permission boundary.

Multiple Developers may implement independent work items. Own assigned files exclusively, including shared test/config files; do not edit another worker's file even for a different function. Report interface changes and affected dependencies before continuing dependent work. Return actual changed paths, checks and unresolved canonical issues for integration.

## Investigator

Answer one bounded code, documentation or root-cause question. Follow applicable project investigation instructions and verify claims against current source or primary documentation; this skill requires no particular indexing tool. Prefer a minimal reproduction or specific source evidence over speculative alternatives. Work read-only except for explicitly assigned isolated diagnostic artifacts; do not edit implementation, broaden scope or dispatch follow-ups.

## Test Engineer

Derive behavioral cases and run meaningful checks on an identified stable integrated snapshot. If assigned to write tests, own their files exclusively and coordinate implementation dependencies through Leader. Report actual commands, outcomes and coverage gaps; tests against a different or actively changing snapshot do not verify the delivered result. Do not present tests you authored or your own implementation as an independent review. A separate QA/Reviewer must cover code you wrote when independent QA is required.

## QA / Reviewer

Independently derive behavioral acceptance cases where useful. Review the actual stable changes against those cases; distinguish confirmed defects from hypotheses. Run appropriate checks when permitted, recording PASS, FAIL, NOT_RUN or environment limitations. Do not accept Developer's reported test results as independent execution evidence.

Do not edit implementation or spawn agents. Ordinary local build/test artifacts are permitted within task authorization; destructive fixtures, shared services and live data need suitable isolation or existing authorization. If reviewing a snapshot, include relevant uncommitted and untracked changes.

## Specialist

Address a named unresolved domain question with explicit scope and closure criteria. Report evidence, impact and uncertainty to Leader; expertise or a majority does not override another reviewer's finding; any reassigned review responsibility must follow controlled reviewer transfer. Default to read-only review; implementation requires an explicit stage/ownership handoff under the Developer contract. Use a relevant specialist skill when warranted. Do not require this role for routine work.

## Handoff evidence

Return a concise result with worker/role, work-item and canonical issue IDs, inspected snapshot/paths, findings, changed files, actual checks and remaining limitations. Include Spec/Plan pair, reviewed scope and explicit verdict for plan reviews. A reassessment must state which finding changed and what evidence justifies it; silence is not acceptance. Distinguish requested model from observed model only where relevant and supported by metadata.

Keep initial reviewers independent. Leader mediates evidence-based follow-ups. Stop or await a writer before another agent takes ownership of its files.

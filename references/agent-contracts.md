# Delegation contracts

Read before spawning. Resolve user overrides, adaptive model/effort selection and role defaults using [the model routing rules](../SKILL.md). Use the actual native subagent API; do not invent parameters or substitute user-visible chat creation.

## Every delegation

Supply a self-contained request with:
- Role and bounded objective.
- Selected model/effort and any user-pinned fields; pass supported configuration fields through the tool, not only the prompt.
- Relevant requirements, Spec/Plan version pair and acceptance criteria.
- Exact workspace path and file ownership or inspection scope.
- Stage: investigate, plan-review, implement or verify.
- Allowed actions and meaningful stopping conditions.
- Expected evidence and deliverable.
- Task ledger, consumed/reserved allowances and the current dispatch's remaining budget; do not reset or extend them or launch a follow-up cycle yourself.
- Effective root task eligibility and any explicit human task override; agents cannot toggle policy or bypass a saved OFF through their own proposals.
- An explicit instruction not to spawn other agents.

Use supported structured model/effort fields. With an API that permits overrides only for fresh contexts, choose fresh context and include the necessary task information explicitly. Do not rely on inherited history that was not passed. Report fallback selection; missing effective-model metadata is uncertainty, not failure.

## Architect

Work read-only on relevant code and tests. Distinguish observations, inferences and unknowns. Propose the smallest design meeting requirements, affected interfaces/files, dependencies and validation. Respond to specific review findings with evidence. Do not modify files, expand scope, decide unresolved product requirements or delegate further.

## Developer

During plan review, work read-only and assess feasibility, hidden dependencies, setup gaps and unnecessary complexity. Give specific failure scenarios and bounded fixes.

During implementation, edit only assigned files within agreed scope. Preserve existing changes. Run relevant checks; report commands and results accurately. When an assumption breaks, pause affected work and notify Leader. Do not deploy, push or perform unrelated external actions without task authorization. Do not delegate further.

When reusing an agent, explicitly change its stage and send the latest plan, ownership and constraints. A read-only prompt is a behavioral instruction, not a runtime permission boundary.

## QA / Reviewer

Independently derive behavioral acceptance cases where useful. Review the actual stable changes against those cases; distinguish confirmed defects from hypotheses. Run appropriate checks when permitted, recording PASS, FAIL, NOT_RUN or environment limitations. Do not accept Developer's reported test results as independent execution evidence.

Do not edit implementation or spawn agents. Ordinary local build/test artifacts are permitted within task authorization; destructive fixtures, shared services and live data need suitable isolation or existing authorization. If reviewing a snapshot, include relevant uncommitted and untracked changes.

## Handoff evidence

Return a concise result with role, inspected paths, findings, any changed files, actual checks and remaining limitations. Include Spec/Plan version pair and verdict for plan reviews. Distinguish requested model from observed model only where relevant and supported by metadata.

Keep initial reviewers independent. Leader mediates evidence-based follow-ups. Stop or await a writer before another agent takes ownership of its files.

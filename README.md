# Coding Team for Codex

Repository: [chauvbm/coding-team-codex](https://github.com/chauvbm/coding-team-codex).

A Codex skill for proportionate delegation, coordinated implementation and independent verification. The Leader selects useful roles, assigns bounded work and owns integration and the final result. Small tasks can stay solo; substantial independent work can use bounded native subagents within the host's actual capacity and the [governance defaults](references/governance-defaults.json).

This README is a repository guide for users, maintainers and independent reviewers. [SKILL.md](SKILL.md) is the operational entrypoint; its linked references define the detailed workflow. The README does not add authority, approvals or competing operating rules.

## Install and try

Requires Git and Python 3.11 or newer. Clone into your personal skill directory using the folder name `coding-team`. Git refuses an existing nonempty destination; inspect and preserve an existing installation rather than overwriting it.

Windows PowerShell:

```powershell
$skillPath = Join-Path $env:USERPROFILE '.agents/skills/coding-team'
git clone https://github.com/chauvbm/coding-team-codex.git $skillPath
if ($LASTEXITCODE -ne 0) { throw 'Clone failed; inspect the existing destination.' }
python "$skillPath/scripts/coding_team_policy.py" init
if ($LASTEXITCODE -ne 0) { throw 'State initialization failed; preserve and inspect it.' }
```

POSIX shell (use your installed interpreter if named differently):

```sh
skill_path="$HOME/.agents/skills/coding-team"
git clone https://github.com/chauvbm/coding-team-codex.git "$skill_path" &&
python3 "$skill_path/scripts/coding_team_policy.py" init
```

Setup creates eligibility state with global ON; it does not install global instructions. Existing valid state is preserved; missing/corrupt state is not silently reset during use. See [control policy](references/control-policy.md) for custom paths and scope. An explicit task request can authorize relevant team use when saved eligibility cannot be established; it never supplies a missing runtime capability or waives a required gate.

Start a fresh chat to load updated instructions, then ask:

> Use $coding-team to repair this bug with proportionate delegation and independent verification. Preserve unrelated changes.

Use `/coding-team status` to inspect eligibility, `/coding-team off` for this chat or `/coding-team on all` for the global default. These are agent-handled controls, not registered native slash commands. Native delegation and model availability depend on the host. Request SOLO when you want no delegation.

Licensed under [MIT](LICENSE).

### Optional automatic controls

The shipped skill permits implicit invocation for matching tasks; AUTO still selects the smallest useful workflow. To have the agent handle persistent ON/OFF controls even before selecting the skill, optionally run `python <skill-directory>/scripts/coding_team_policy.py install-global-instructions`. This adds only the marked coding-team block to your Codex AGENTS.md, preserving unrelated instructions. It embeds the setup interpreter; regenerate it if that interpreter moves. Start a fresh chat after installation.

For an explicit-only installation, locally change `policy.allow_implicit_invocation` to `false` in `agents/openai.yaml`, then invoke `$coding-team` when wanted. Preserve other YAML fields. This is a host skill-selection option; it does not replace saved per-chat ON/OFF controls, stop running workers, or change existing gated work.

## Start here

Review the exact branch or commit supplied by the owner. Record the checked-out revision before assessing findings or test results:

```text
git rev-parse HEAD
```

Reading this repository does not require installing the skill or changing Codex configuration. The Python helper and checker tests use the standard library. Executing real delegated work additionally requires a host exposing native subagent tools and suitable authorization. [Model routing](references/model-routing.md) and [profiles](references/model-profiles.json) describe configuration and fallback; model availability is not supplied by this repository.

## Repository map and reading order

| Read | File | Purpose |
| --- | --- | --- |
| 1 | [SKILL.md](SKILL.md) | Scope, modes, role/model routing, capacity and essential gates |
| 2 | [workflow.md](references/workflow.md) | Work selection, dependencies, ownership and integration |
| 3 | [agent-contracts.md](references/agent-contracts.md) | Bounded handoffs and each worker's responsibilities |
| 4 | [debate-governance.md](references/debate-governance.md) | Canonical issues, evidence, counters, termination and scoped approvals |
| 5 | [quality-safety.md](references/quality-safety.md) | Verification, recovery and accurate reporting |
| 6 | [control-policy.md](references/control-policy.md) | ON/OFF commands, precedence, state and bootstrap behavior |
| 7 | [governance-defaults.json](references/governance-defaults.json) | Single source for numeric operational defaults |
| 8 | [coding_team_policy.py](scripts/coding_team_policy.py) | Deterministic policy persistence and marked instruction installation |
| 9 | [task-ledger.md](references/task-ledger.md) | Optional durable task records and readiness stages |
| 10 | [task_ledger.py](scripts/task_ledger.py) | Atomic ledger updates, history and structural readiness checks |
| 11 | [openai.yaml](agents/openai.yaml) | Skill UI metadata and implicit-invocation policy |
| 12 | [tests/](tests/) | Behavioral fixtures and checker, policy and ledger regression tests |

Read references conditionally as directed by SKILL.md; the numbered map is for repository review, not a mandatory runtime reading list. Model profiles default to inheriting the runtime configuration; users can configure role preferences once without hardcoding account-specific models into the entrypoint. See [CONTRIBUTING.md](CONTRIBUTING.md) for maintenance and portable release archives.

For a static quality review, inspect both the operating instructions and the test oracles. For a blind behavioral evaluation, keep the oracles away from the evaluating agent as described below. Generated `graphify-out/` files are local development aids and are not required to review or run the skill.

## How the team operates

The core responsibilities are Architect, Developer and independent QA/Reviewer, coordinated by the Leader. Investigator, Test Engineer and Specialist roles support specific needs; multiple Developers can own independent work items. Roles are responsibilities, not a required number of agents.

The concurrency ceiling is `max_subagents` in [governance defaults](references/governance-defaults.json), excluding Leader and constrained by runtime capacity, active agents and user limits. `FULL_TEAM` covers the core review responsibilities without requiring all slots. Shared files have one writer at a time. Independent QA examines a stable integrated result, rather than relying on individual workers' summaries.

Review starts independently on an identified version. Leader then merges duplicate findings without losing attribution and routes each issue only to its relevant owner and reviewers. Majority votes do not resolve defects. Material changes require affected reassessment; unrelated valid reviews need not restart indiscriminately.

## Preventing repetitive debate

The authoritative rules and accounting details are in [debate governance](references/debate-governance.md). The distinctions important to a review are:

- Numeric allowances live only in [governance-defaults.json](references/governance-defaults.json): concurrency, no-progress exchanges, per-level revision cycles, per-defect/task repair, diagnostics, recovery and focused-review deadlines. They are shared across workers, not multiplied by team size.
- The [checkpoint decision matrix](references/debate-governance.md) defines evidence transitions and STOP_HOLD. Without applicable human continuation, unresolved revision/repair limits stop the loop. Prior explicit authority can permit an evidenced next batch without another count-only permission request.
- Continuation preserves history and cannot extend no-progress, diagnostic, recovery or deadline limits, grant external permissions or supply missing approval. A required gate remains HOLD until its current approvals and material findings are resolved.

Human continuation authority and any quota-pause preference are task context, not assumptions every installation inherits. Tests explicitly supply the relevant context for each scenario. The skill honors an applicable quota threshold only when trustworthy remaining-usage information is available.

## Policy controls and enforcement boundary

The skill recognizes `/coding team on`, `/coding team off`, their `all` variants, `/coding team status` and `/coding team inherit`, with `/coding-team` accepted for every command. Policy is checked for direct controls, before applying coding-team and freshly before each dispatch; routine SOLO explanations need no per-turn shell check. Chat policy takes precedence over the global default; an explicit human request can authorize team use for its task. ON permits relevant delegation but does not dispatch work, approve a plan or reset a ledger.

[Control policy](references/control-policy.md) documents state location, actual chat identity requirements and setup. `init` and `install-global-instructions` are setup operations that write state or instructions; they are not prerequisites for a read-only repository review. When testing the helper, use isolated `--state` and, for instruction-installation tests, `--agents` targets rather than the user's live files.

The eligibility helper uses locking and atomic writes for policy storage. The optional [task ledger](references/task-ledger.md) additionally validates recorded counters, ownership, approval versions and readiness. These checks operate on caller-authored records, not native tool calls; neither helper intercepts agents, locks implementation files, authenticates human authority or proves that a claimed review ran. The host enforces its own permissions and concurrency. Passing behavioral fixtures does not turn instructions into runtime locks.

## Checks you can run locally

Run commands from the repository root using your Python 3 interpreter:

```text
python -m unittest discover -s tests -p "test_*.py" -v
git diff --check
```

The unit suite covers the response checker, eligibility helper and task ledger, including malformed state, counter/history resets, hold/pause readiness, stale approvals, reviewer transfers, path escapes, concurrent updates and atomic-write failures. It does not execute the skill's behavioral scenarios. Inspect the current test files for the test inventory rather than treating a fixed count as a coverage guarantee.

If the Codex skill-creator validator is available in your environment, run its `scripts/quick_validate.py` against this repository as an additional structural check. It is an external development utility, not bundled here, and does not establish behavioral correctness.

## Independent behavioral evaluation

The fixtures contain:

| Fixture | Inventory | What it probes |
| --- | --- | --- |
| [behavioral_cases.json](tests/behavioral_cases.json) | 24 independent scenarios | Review independence, duplicates, stale approval, vote pressure, capacity, ownership, continuation, missing reviewers and quota pause |
| [sequential_cases.json](tests/sequential_cases.json) | Four ordered turns of one issue | Evidence cutoff, stopping a stalled diagnostic, rejecting renamed retries and resuming repair on new evidence |
| [reviewer_transfer_cases.json](tests/reviewer_transfer_cases.json) | Six independent scenarios | Verified successor reassessment, independence, version, deadline and history preservation |

Each fixture stores `instructions`, scenario `input` and expected `checks`. These are decision simulations; they do not implement the fictional tasks, dispatch their workers or execute their proposed checks. Historical evaluator outputs and provenance are published in [the decision evaluation record](evaluations/2026-10-31-decisions/README.md). They are pinned to earlier commits and are not evidence of a fresh run on the current checkout.

Use a separate coordinator to prepare blind inputs with the tested exporter. It creates a temporary skill snapshot and one numbered input file per case, omitting tests, expected checks and published results:

```text
python scripts/export_evaluation_inputs.py --cases tests/behavioral_cases.json
python scripts/export_evaluation_inputs.py --cases tests/sequential_cases.json
python scripts/export_evaluation_inputs.py --cases tests/reviewer_transfer_cases.json
```

The printed directory contains `skill/` and `inputs/`. An optional `--output` must name a new directory outside this repository; existing destinations are refused. This is coordinator preparation, not access enforcement. For sequential cases reveal each numbered input only after the previous response.

Give a fresh evaluator the isolated skill and only the inputs assigned to it, with permission to write its JSON responses to a separate output location. Do not provide `checks`, the scorer, peer verdicts or previous expected results. Do not reuse an agent that already inspected the oracles as a blind evaluator. Copying files alone is not a security sandbox; control tool/filesystem access if stronger isolation is required.

Independent scenarios can be grouped into bounded batches. For the sequential fixture, use the same evaluator across its four turns, reveal only the next input after the previous response, and preserve its history. Keep future observations coordinator-only. Apply the human authority stated in each scenario, not unrelated personal preferences from the evaluator's environment. Do not allow the simulations to dispatch agents or mutate live configuration.

Collect responses as JSON arrays following the fixture's instructions, then score them from the original repository. Replace the example response paths with actual generated files; more than one response file is accepted:

```text
python tests/check_behavioral_results.py path/to/independent-responses.json
python tests/check_behavioral_results.py --cases tests/sequential_cases.json path/to/turn1.json path/to/turn2.json path/to/turn3.json path/to/turn4.json
```

The checker exits with code 0 when all expected cases are present and its assertions pass, or 1 for decision failures. Inspect the actual rationales and transcripts as well: structured answers can satisfy assertions while concealing contradictions. Neither a passing scorer nor a previous success claim proves reliable performance on every real task.

## Brief for a specialist reviewer

Provide the full repository at the intended revision, not just this README. A suitable static review request is:

> Review the quality of this Codex skill at the checked-out commit. Read README.md, SKILL.md, the linked references, helper and tests. Work read-only apart from isolated test artifacts. Do not install the skill or change live policy/configuration. Check scope, instruction consistency, proportional delegation, review independence, approval freshness, termination and continuation rules, and whether tests can falsely pass unsafe decisions. For each actionable finding, give severity, file/line evidence, a concrete failure scenario and the smallest correction. Distinguish executed checks from unrun ones and runtime enforcement from behavioral instructions. Do not fix the skill during this review.

An agent performing this static review may inspect the expected checks. If behavioral evaluation is also required, run it afterward in fresh contexts using the blind protocol above. Record the reviewed commit, relevant human authority, evaluator configuration when known, actual outputs, failures and coverage limits. New adversarial scenarios are useful for checking whether the supplied fixtures miss a failure mode.

## Published evaluation evidence

Historical [34 decision responses](evaluations/2026-10-31-decisions/README.md) pin their source commits and protocol corrections. The [six-task coding pilot](benchmarks/coding-pilot/README.md) publishes actual repaired snapshots and withheld acceptance results for SOLO, AUTO and FULL_TEAM. All three passed; this small synthetic sample does not establish a team advantage or cost saving.

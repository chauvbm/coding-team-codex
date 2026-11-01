# Cross-module strict dotenv bundle

This fixture uses four unchanged, actual upstream Python modules plus their
license, pinned in `sources.json`. The task requests a new opt-in feature; it
does not characterize the baseline as an upstream defect. The package uses only
Python's standard library. `TASK.md` is the complete participant-facing contract.

The coordinator retains `acceptance.py` and `score.py`. Copy only `baseline/`
contents and `TASK.md` into a fresh participant workspace, plus condition-specific
skill instructions where required by the execution protocol. Never expose oracle
files, prior attempts, final results or previous answers to a participant.

Replay on any candidate package root:

```powershell
python benchmarks/cross-module/score.py --workspace <candidate-root>
```

The scorer uses a fresh isolated subprocess, a 45-second timeout and an exact
28-test inventory. Skips, expected failures, missing/extra tests, process errors,
and incomplete execution reject the candidate. JSON includes per-test outcomes;
exit codes are 0 accepted, 1 acceptance rejected, 2 execution/inventory failure.
The acceptance contract checks parser context, lower-level variable behavior,
public integration, source-order precedence, environmental snapshot semantics,
zero-write error transactions, caching and permissive-mode regressions.

The experiment contains **one task bundle**, repeated five times per condition:
CONTROL (single coder) and AUTO (coder plus independent QA and bounded repair).
Five repetitions are repeated attempts on the same task, not five distinct tasks
or evidence about a population of tasks. AUTO receives extra QA/repair compute;
the conditions are not matched for model calls or compute. Timing and token/cost
reporting belong to the coordinator's run ledger. Unattributable telemetry must
remain null; do not infer token or cost savings from elapsed time.

This benchmark author supplies no reference implementation. Baseline failure
establishes that the acceptance suite demands behavior absent from the pinned
source; it does not by itself prove that every assertion is satisfiable. Contract
review and prospective participant results must be reported separately.

## Frozen repeated results

The evaluated skill snapshot is `fda0779294fba06120eb54f1f159580615959ea3`,
identified by `skill-snapshot.json`. Later test-portability corrections did not
change those operational files. `freeze.json` records the contract/source hashes,
five pairs, randomized dispatch order, budgets and unmatched-compute limitation.
The task and acceptance were clarified and independently reviewed before dispatch.

| Condition | Fully accepted trials | Acceptance in each trial | Native workers per trial | Observed delivery median |
| --- | --- | --- | --- | --- |
| CONTROL, coder/self-check | 5/5 | 28/28 in all five | 1 | 89.45 s |
| AUTO, coder/independent QA | 5/5 | 28/28 in all five | 2 | 162.46 s |

Each AUTO reviewer approved after inspecting the actual stable code and running
independent probes. No QA-driven repair was requested. The coordinator captured
all ten final snapshots before running hidden acceptance; no participant received
hidden-test feedback and no post-score repairs or extra trials were performed.
All ten runs returned exit 0, without skips or expected failures. No acceptance
failure remained after QA, but this does not estimate QA's defect-detection rate
because the control snapshots also passed every acceptance test.

`results/<condition>-NN/` preserves package code, LICENSE, public TASK, coder
REPORT, independent QA reports/probes where applicable, and raw `acceptance.json`.
Local graphs and bytecode caches are excluded. `summary.json` contains prospective
dispatch requests, coordinator-observed completion stages, normalized file hashes,
raw outcomes and descriptive timing ranges. Full native tool transcripts are not
bundled. Instruction-scoped isolation was not a filesystem sandbox.

These are five fresh-context attempts per condition on **one four-module source
subset**, not five different repositories or a full upstream regression suite.
The same inherited model/effort configuration was requested, but observed model
metadata was unavailable. Conditions ran concurrently within each pair; timing
includes queueing, coordinator scheduling, graph work, self-checks and AUTO QA.
The dispatch timestamps precede API calls rather than proving actual execution
start. Timings are observations, not controlled latency measurements. AUTO used
extra review compute; token and cost data remain null.

The result is a tie at this acceptance ceiling. It establishes neither a quality
advantage for AUTO nor token/cost savings, and does not justify broad speed or
production-quality claims. All original historical evaluations remain unchanged.

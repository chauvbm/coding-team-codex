# Repository maintenance pilot

This task uses actual unmodified source from coding-team-codex `6055037c`, not newly invented utility functions. [TASK.md](TASK.md) specifies transactional ledger commands and safe evaluation export. The acceptance contract and 15 tests were frozen before dispatch; their hashes and output hashes are recorded in [summary.json](results/summary.json).

| Mode | Distinct agents | Dispatches including role handoffs | Parallel implementation writers | Windows available checks |
| --- | ---: | ---: | ---: | --- |
| SOLO | 1 | 1 | 1 | 10 pass, 5 skipped |
| AUTO | 2 | 2 | 1 | 10 pass, 5 skipped |
| FULL_TEAM | 4 | 6 | 2 | 10 pass, 5 skipped |

SOLO used one coder and self-checks. AUTO added independent final QA. FULL_TEAM obtained three independent initial s1/p1 plan verdicts, recorded gate PASS in PLAN.json, then handed separate ledger/export files to two Developers concurrently and reused the independent QA for the stable integrated result. Extra plan/role handoffs count as dispatches, not additional people. The unmodified baseline fails acceptance.

Windows lacked privileges for five actual symlink tests; do not report 15/15 from those local runs. Developer/QA reports separately distinguish native junction probes and simulated symlink metadata. CI replays all three implementations on Linux and requires all 15 tests with zero skips. A successful CI replay verifies the frozen implementations, not a new model run.

```text
python benchmarks/repository-maintenance/score.py --workspace benchmarks/repository-maintenance/results/full_team
```

The scorer reports `passed_available_checks` separately from `accepted` (all checks, no skips). Exit 0 means available checks pass; inspect coverage before claiming full acceptance. CI's Linux regression explicitly requires complete coverage.

The participants were separate native subagents, given the same baseline and no coordinator acceptance or peer-mode outputs. Isolation was instruction-scoped. Source/script snapshots, author reports, independent QA reports and the full-team plan gate are published; full tool/model transcripts are not. Self-check source files are not bundled. Root recorded delivery and gate observations, but reliable comparative elapsed times, token costs and observed model metadata were unavailable and remain null. No repair was made after hidden acceptance feedback.

This remains **one task, one run per mode, from the skill's own repository**. All modes passed the available checks, so this experiment does not establish a team quality or speed advantage. It does exercise actual parallel file ownership, a plan gate and integrated independent QA. Agent cancellation, contested-plan repair and post-QA code invalidation were not injected here. Broader real-repository, repeated, randomized and resource-matched comparisons remain necessary before efficiency claims.

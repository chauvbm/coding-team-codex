# Six-task coding pilot

This is a small **synthetic** maintenance pilot, not a production benchmark or proof that a team outperforms SOLO. The [contract](TASKS.md) covers six utilities: pagination, merge independence, graph ordering, CSV validation, cache expiry and atomic transfers. The deliberately defective [baseline](baseline/utilities.py) fails every task group.

An independent QA author read only the contract and wrote 36 acceptance tests. They were withheld from coders and role reviewers by instruction during the run; they are now [published](acceptance/test_contract.py). No post-acceptance failure feedback or repair was given.

| Mode | Actual staffing | Accepted tasks | Acceptance tests |
| --- | --- | --- | --- |
| SOLO | One coder, self-checks | 6/6 | 36 passed |
| AUTO | One coder, independent final QA | 6/6 | 36 passed |
| FULL_TEAM | Independent Architect, Developer and QA plan review; explicit gate; Developer implementation; independent final QA | 6/6 | 36 passed |

All roles requested the same model and effort, recorded in [summary.json](results/summary.json), against skill commit `151856b5e98f01fe5ae5bd6a8d20abd591ec5a65`. Effective backend metadata and per-run token/cost telemetry were unavailable. The coordinator selected AUTO staffing; autonomous team-size selection was not measured.

Each mode ran once, and runs overlapped on one host. Observed timestamps contain dispatch, queueing and polling overhead; the FULL_TEAM finish timestamp was not retained. They do not support a reliable latency comparison. Structured worker reports, review/gate records, self-checks, source snapshots and acceptance outputs are provided under [results/](results/); full tool/model transcripts are unavailable. Personal paths were replaced with placeholders. Graph workflow deviations are preserved in the reports rather than described as full compliance.

Reproduce acceptance from the repository root:

```text
python benchmarks/coding-pilot/score.py --workspace benchmarks/coding-pilot/results/solo
python benchmarks/coding-pilot/score.py --workspace benchmarks/coding-pilot/results/auto
python benchmarks/coding-pilot/score.py --workspace benchmarks/coding-pilot/results/full_team
python benchmarks/coding-pilot/score.py --workspace benchmarks/coding-pilot/baseline
```

The first three should return exit 0. The baseline should return exit 1. Exit 2 denotes an execution/import error. The runner starts a fresh process and rejects skipped acceptance tests; it is not a security sandbox for untrusted code.

The equal scores show that all three runs met these particular contracts. They establish neither a quality advantage nor cost efficiency. A stronger study needs unseen production tasks, repeated randomized runs, a consistent execution schedule, independent defect adjudication and complete token/latency accounting.

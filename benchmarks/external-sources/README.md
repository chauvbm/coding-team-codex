# External-source feature pilot

Three isolated modules were downloaded from pinned upstream commits before dispatch. [sources.json](sources.json) records exact source URLs, revisions and SHA256 values. Upstream source/attribution and licenses are retained beside every baseline and modified module. These third-party files remain under their own licenses; the skill's MIT license does not replace them.

Published text is UTF-8/LF. Provenance distinguishes original downloaded byte hashes and line endings from canonical published hashes; replay verifies both, reconstructing original CRLF where needed. This is newline normalization, not a source-logic change.

| Source | Requested addition |
| --- | --- |
| [boltons](https://github.com/mahmoud/boltons) mathutils | Lazy, bounded `clamp_iter` |
| [more-itertools](https://github.com/more-itertools/more-itertools) recipes | Combinatorial `combination_index` without enumerating the search space |
| [python-dotenv](https://github.com/theskumar/python-dotenv) parser | Ordered mapping with strict syntax-error reporting |

The modules were renamed to `module.py` for standalone stdlib imports. These are requested experimental feature additions, not fixes to claimed upstream bugs, full repository integration tasks or a representative sample of production work. [TASK.md](TASK.md) and the 18 acceptance tests were frozen before participant dispatch. All three tasks were bundled into one run per condition, rather than treated as independent repeated trials.

| Condition | Unique subagents | Dispatches/stage handoffs | Parallel implementation writers | Frozen acceptance |
| --- | ---: | ---: | ---: | --- |
| General coding, no skill | 1 | 1 | 1 | 18/18 |
| SOLO with skill | 1 | 1 | 1 | 18/18 |
| AUTO with skill | 2 | 2 | 1 | 18/18 |
| FULL_TEAM with skill | 4 | 6 | 2 | 18/18 |

FULL_TEAM used independent Architect, Developer and QA initial plan reviews, recorded gate PASS, then handed two modules to Developer-A and the parser to Developer-B concurrently. Independent QA checked the stable integration. AUTO used one coder and independent final QA. Control and SOLO used self-checks. No hidden-acceptance feedback was supplied to participants and no production code was repaired after acceptance. All modes inherited the same parent runtime configuration; actual observed model/effort and token/cost telemetry were unavailable.

The FULL_TEAM Developer-A self-check batch reported FAIL because of an incorrect legacy Bits assertion and two package-dependent upstream doctests. This report is preserved. Separate QA found no feature defects; root replay confirmed the same two doctest failures exist in the unchanged isolated baseline (138/140 in both), recorded in upstream-doctest-comparison.json. Do not describe this as a passing full upstream suite. Original self-check/QA source files are not bundled; their reports and frozen production implementations are.

```text
python benchmarks/external-sources/score.py --workspace benchmarks/external-sources/results/full_team
```

The scorer runs in a fresh subprocess with a 45-second bound, rejects skips or a missing test inventory, and makes no model/network calls. CI replays all four snapshots and verifies that the unmodified baseline fails. Source/contract/acceptance hashes are checked separately.

Results still tie: **this pilot does not demonstrate a quality, speed or cost advantage for the team**. Prospective dispatch and coordinator-observed delivery timestamps are published in summary.json, but conditions ran concurrently and timings include queueing, review and coordinator scheduling. They are observations, not controlled comparative latency. Token/cost remain null; account-wide quota cannot attribute per-task usage. One run, no randomized ordering, no matched total compute budget, instruction-scoped isolation and unavailable full transcripts limit any inference. A broader repeated study with attributable telemetry remains future work.

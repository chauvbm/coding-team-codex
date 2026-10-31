# Protocol v3 decision evaluation

Two fresh agents evaluated the same 16 frozen situations on operational source `218e3991c7537b773a82f89601a4b072f3d73db0`. One received the exported skill and relevant references; the control received only scenario inputs and the common response protocol. Neither received expected checks, previous verdicts or peer responses. Both reported reading no prohibited resources. The coordinator froze inputs and source fingerprints before dispatch; each condition ran once, without a score-seeking retry.

| Condition | Raw cases passed | Failed case IDs |
| --- | --- | --- |
| With skill | 14/16 | r15, r16 |
| No-skill control | 13/16 | r03, r15, r16 |

The [fixture](fixture.json), raw response files, [freeze record](freeze.json) and [summary](summary.json) preserve the exact checks and failures. A regression check replays these results; it does not constitute a fresh agent evaluation.

The shared r15 failure uses `organize_correction` for supported responsibility migration; both rationales preserve history and require distinct reviewers and a fresh plan pair. The oracle accepts only `plan_repair`, `independent_review` or `hold`. In r16 both agents reject deleting or cancelling the unfinished requirement, then schedule its completion and permit implementation. The scenario states no implementation gate or overlapping writer, while the oracle requires a non-writing next step. However, permission to write also assumes ownership/readiness facts that were not established. This ambiguity warrants caution; the responses do not demonstrate permission to drop required work. The control's r03 response completes a findings-only review without permitting writes; the checker excludes `complete` for this case. No post-hoc adjusted score replaces the raw results.

Both conditions retain unfinished ACTIVE work in r13 and preserve reviewer A's unresolved rejection in r14. These are decision simulations, separate from the executable ledger regressions and independent core/package QA.

An [independent evidence audit](independent-review.md) reproduced the raw scores and reviewed all rationales. It also notes that the control's r09 plan-gate field is imprecise and unchecked by the oracle. No material runtime defect was established by these decision artifacts.

All scenarios within each condition share one context. Isolation is instruction-scoped on a shared filesystem, not a runtime sandbox. The runtime model and effort were inherited with no overrides; observed model, token usage and cost were unavailable. Inputs explicitly provide workflow facts and a response schema. One run per condition cannot establish population accuracy, coding quality, cost savings or a skill advantage; the one-point raw difference is affected by action taxonomy. Historical v2 artifacts and scores remain unchanged.

Replay with `python tests/check_behavioral_results.py --cases evaluations/2026-11-01-protocol-v3/fixture.json evaluations/2026-11-01-protocol-v3/skill-responses.json` (and separately `control-responses.json`). Both commands intentionally return exit 1 for preserved raw failures.

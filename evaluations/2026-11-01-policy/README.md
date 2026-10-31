# Policy and decision re-evaluation

All 42 existing scenarios were evaluated anew on one operational snapshot identified by the UTF-8/LF hashes in summary.json (core commit dd30de4). A neutral protocol clarification defines `ownership_handoff` as implementation write ownership; reviewer transfer uses review actions. The original historical fixture files and expected checks were not modified. Sequential inputs were revealed one at a time to the same evaluator.

| Batch | Raw result |
| --- | --- |
| Existing behavioral scenarios | 22/24 |
| Reviewer transfer | 6/6 |
| Modes and levels | 8/8 |
| Sequential four-turn issue | 4/4 |
| **Existing total** | **40/42** |
| New realistic scenarios, with skill | 11/12 |
| Same realistic inputs, without skill | 10/12 |

The new [fixture](../../tests/realistic_cases_v2.json) uses neutral IDs and ordinary situations without naming scenario-specific bad-answer fields. It still supplies a common output schema and explicit workflow facts; this is not an unprompted coding-performance test. An independent reviewer inspected every failed response. Both old behavioral failures propose safe corrections but use a broader action enum than the scorer permits. Both realistic groups describe stopping the old writer and inspecting WIP before transfer, yet label the immediate action `ownership_handoff`. Neither permits overlapping writes.

The remaining control discrepancy is ambiguous: the response correctly completes the self-checked task but sets `can_write_affected` false. The oracle expected true as permission, whereas a completed task can reasonably have no next write. Raw scores and checks remain unchanged. **The one-point gap therefore does not demonstrate a benefit from the skill.** No extra evaluator run or oracle edit was used to manufacture a passing score.

The skill and control used parent runtime inheritance with no model/effort override; observed model, tokens and cost were unavailable. Input-only, fresh-agent isolation was instruction-scoped, not a filesystem sandbox. One run per batch/condition cannot estimate population accuracy, cost, safety or efficiency. Full transcripts are not bundled. Published copied fixtures include their exact protocol and frozen checks for replay; only inputs and operational skill files were supplied to evaluators.

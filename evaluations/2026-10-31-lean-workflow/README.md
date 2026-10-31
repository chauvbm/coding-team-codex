# Lean workflow decision test

A fresh evaluator received an isolated operational skill snapshot and input-only scenarios, without oracles or prior verdicts. Eight mode/level cases and six reviewer-transfer cases were scored against frozen checks. Source snapshots are identified by canonical UTF-8/LF file hashes in summary.json; the initial draft and corrected draft are distinct.

Initial raw result: **11/14**, comprising mode coverage **8/8** and transfer coverage **3/6**. Independent QA found two action-enum mismatches: answers described a correct controlled review transfer but labeled it `ownership_handoff`, while the oracle expected review/correction enums. Both retained HOLD, independence, attribution and counters. The third response unnecessarily requested continuation authority after recovery/deadline exhaustion; it still stopped without dispatching or extending anything. Raw outputs and original checks are preserved unchanged.

The governance reference was clarified to report STOP_HOLD blockers first and ask only for a concrete required user decision/authorization. A different fresh evaluator then answered only the failed escalation scenario: **1/1**. This is a targeted retest, not a claim of 14/14 on the corrected snapshot. No oracle was amended to make answers pass.

These are decision simulations, not native execution or reliable measurements of accuracy, token costs or latency. Evaluator isolation was instruction-scoped. Full transcripts/observed model/token metrics are unavailable; summary.json leaves them null. Historical results from the earlier evaluation directory remain separate.

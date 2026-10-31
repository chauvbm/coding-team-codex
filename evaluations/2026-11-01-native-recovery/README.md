# Native recovery exercise

A small coordinator-authored invoice task exercised real native subagent actions. This is an AUTO workflow with a required scoped independent-QA plan gate, not a FULL_TEAM benchmark or a runtime enforcement test.

1. Independent QA rejected p1 for ignoring tenant isolation. Covered implementation remained HOLD.
2. The coordinator called native `interrupt_agent` on that reviewer; the tool returned `previous_status: running`. The successor received the historical rejection, closure criteria, p2, counters and original deadline, directly reassessed p2 and approved it.
3. After gate PASS, a Developer created partial WIP. A second native interrupt returned `previous_status: running`. Root inspected and saved its exact hash/content, transferred exclusive ownership, and completed C1.
4. Independent successor QA verified C1 with eight tests and returned PASS.
5. Root deliberately injected an integration regression as C2. C1's approval was marked stale before delivery; the same independent QA reran affected tests, found the regression and returned FAIL, preserving its former PASS.
6. Root performed one bounded repair to C3. Independent QA freshly verified C3 and closed the original findings. All prior verdicts and snapshots remain published.

The record consumes one plan revision, two recoveries for distinct review/writer operations and one implementation repair batch. Neither reviewer replacement nor repair renewed the original phase deadline. `recovery-record.json` records coordinator-observed tool results, source snapshots, counters and evidence paths. It is not a tamper-proof transcript or authenticated proof of native tool enforcement. Cancellation was controlled interruption, not a crashed or malicious host process. A cancelled agent's historical dissent was retained throughout.

The faults were injected on purpose and must not be counted as spontaneous model mistakes or evidence that a team outperforms SOLO. Replay tests verify that C1/C3 pass and C2 fails the frozen contract; they do not repeat the original native interrupts. Source hashes show C3 restores C1 content; it still required an explicit renewed current verdict rather than silently reusing C1 approval. Token, cost and comparative timing were not measured.

Published text is normalized to UTF-8/LF. Original byte hashes remain unchanged in the historical QA verdicts; the record maps those hashes to the canonical snapshots and retains each original newline sequence (the WIP file had mixed LF/CRLF). `qa_checks-original.txt` preserves the last independent test source before portability adaptation. The executable `qa_checks.py` changes only its source-hash calculation/expected hash to canonical UTF-8/LF; its eight behavioral tests are unchanged.

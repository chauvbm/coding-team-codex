# s1/p1 repair plan

Scope: satisfy all six contracts in TASKS.md, preserving signatures and standard-library-only operation. One implementation Developer owns utilities.py and may add local self-checks. No worker reads coordinator acceptance or another run.

Investigate each function against its contract; repair the independent utility behavior, then run local behavioral checks including invalid input, input independence, ordering and boundary cases. Check interactions on a stable final utilities.py snapshot. No production services, external calls, installs or policy changes.

Implementation begins after Architect design acceptance and independent Developer feasibility and QA acceptance review of s1/p1. Parent Leader records gate and transfers ownership. After implementation, independent QA inspects actual diff/snapshot and runs checks; coordinator then runs previously withheld acceptance. Do not claim tests not executed or treat plan approval as final verification. Any material contract change requires affected review. Canonical numeric allowances apply, no nested delegation.

# Independent QA — AUTO trial 01

APPROVED

Reviewed the stable delivered four-module package (`dotenv/main.py`, `parser.py`, `variables.py`, `__init__.py`) against TASK.md. Queried the existing graph before reading package source. No production source edits, policy changes, delegation, or commits were made.

No BLOCKER or MAJOR findings. Independent checks exercised public signatures and exports, parser recovery and strict errors, binding metadata with CR/LF/CRLF and multiline/leading whitespace, source-order and same-binding error precedence, duplicate valueless keys, repeated atom resolution and recognized/unrecognized syntax, absent/present-empty/present-None/default semantics, ordered dictionaries and override precedence, missing self/forward references, snapshot-before-read behavior, transactional zero-write failures including skipped assignments, successful return/commit behavior, interpolation disabled, cache retry and successful-cache identity, permissive recovery, and disabled loading.

Commands actually run from this workspace:

- `graphify query "strict dotenv parsing interpolation validation"`: PASS; graph identified relevant package relationships. Output was truncated to the chosen display budget, so all four source modules were directly reviewed afterward.
- `C:/Program Files/Python313/python.exe qa_probe_contract.py`: PASS, 14 independently authored unittest methods, including table-driven matrices. The permissive-recovery warning is expected.
- `C:/Program Files/Python313/python.exe -m unittest -v test_strict`: PASS, 11 coder tests as supplemental regression evidence, after the independent probes.

Transaction scenarios: each of parse failure, duplicate failure, and undefined expansion after a valid NEW definition raised the expected DotEnvError and recorded zero writes for both override settings. An undefined value on an existing OS key was also validated rather than silently skipped.

A file inventory confirmed this bundled standard-library package consists of four modules. Attempts to read absent cli.py/ipython.py/__main__.py/version.py reported missing files; no behavior of unavailable modules is claimed. No external dependency or hidden acceptance suite was used. Arbitrary OS assignment failures and concurrent OS writers are outside TASK.md's guarantee and were not tested.

Independent probe artifact: qa_probe_contract.py.

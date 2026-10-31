# Maintenance and evaluation

Run the stdlib regression suite and `git diff --check` before publishing. When available, run the external skill-creator `scripts/quick_validate.py` too. CI runs the suite on Windows/Linux and Python 3.11/3.13, including historical decision replay and coding-pilot acceptance. A passing replay proves artifact/checker consistency, not that the current skill produced those decisions again.

For a substantial instruction change, use fresh independent evaluators with realistic requests. Export only inputs and operational resources with `scripts/export_evaluation_inputs.py`; keep the oracle and prior verdicts coordinator-only. Freeze acceptance checks before dispatch. Preserve failures and protocol corrections rather than changing expectations to obtain a pass. Review rationales and actual artifacts as well as structured scores. Instruction-scoped isolation is not a filesystem sandbox.

Measure context using an actual tokenizer/host telemetry when available. Word/character counts are useful size indicators but not measured input, output or reasoning tokens. Report unavailable token/cost data as null; account-wide quota deltas cannot attribute usage to a particular worker.

## Portable archives

Distribute a named committed revision, rather than zipping the working directory:

```text
git archive --format=zip --output=../coding-team-codex.zip HEAD
```

Use a new output filename if an archive already exists. Git archive includes only committed files, so local graphs, caches, private state and untracked artifacts stay out. `.gitattributes` makes text checkouts LF; historical published SHA256 values refer to UTF-8 text with LF newlines. Do not replace historical evidence merely to make it appear current.

Project-specific tools such as graph indexers are optional development aids, not skill prerequisites. Keep their generated files out of release archives and runtime instructions. New helpers should preserve policy and task history and should not claim to authenticate human authority or intercept native tools.

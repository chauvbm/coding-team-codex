# Maintenance and evaluation

Run the stdlib regression suite and `git diff --check` before publishing. When available, run the external skill-creator `scripts/quick_validate.py` too. CI runs the suite on Windows/Linux and Python 3.11/3.13, including historical decision replay and coding-pilot acceptance. A passing replay proves artifact/checker consistency, not that the current skill produced those decisions again.

For a substantial instruction change, use fresh independent evaluators with realistic requests. Export only inputs and operational resources with `scripts/export_evaluation_inputs.py`; keep the oracle and prior verdicts coordinator-only. Freeze acceptance checks before dispatch. Preserve failures and protocol corrections rather than changing expectations to obtain a pass. Review rationales and actual artifacts as well as structured scores. Instruction-scoped isolation is not a filesystem sandbox.

`tests/realistic_cases_v3.json` is a new protocol, separate from the frozen v2 evaluation. It distinguishes preparation from an actual ownership transfer and defines `can_write_affected` as permission for the immediate next implementation step; completion does not require another write. Four added situations cover unfinished work, unaddressed final-review rejection, legacy responsibility repair and unsupported cancellation. The v3 fixture has not yet been evaluated by a fresh blinded agent; no v2 scores are rewritten or counted as v3 results.

Measure context using an actual tokenizer/host telemetry when available. Word/character counts are useful size indicators but not measured input, output or reasoning tokens. Report unavailable token/cost data as null; account-wide quota deltas cannot attribute usage to a particular worker.

## Portable archives

Distribute a named committed revision, rather than zipping the working directory:

```text
git archive --format=zip --output=../coding-team-codex.zip HEAD
```

Use a new output filename if an archive already exists. Git archive includes only committed files, so local graphs, caches, private state and untracked artifacts stay out. `.gitattributes` makes text checkouts LF; historical published SHA256 values refer to UTF-8 text with LF newlines. Do not replace historical evidence merely to make it appear current.

Project-specific tools such as graph indexers are optional development aids, not skill prerequisites. Keep their generated files out of release archives and runtime instructions. New helpers should preserve policy and task history and should not claim to authenticate human authority or intercept native tools.

## Runtime-only installation package

For end users, run `python scripts/build_runtime_package.py --output ../coding-team-runtime.zip` from a stable checkout. Omit `--output` for a new temporary destination. Existing destinations are refused. This package includes only LICENSE, SKILL.md, agents, references and scripts under `coding-team/`, plus a manifest with canonical UTF-8/LF hashes and sizes. It excludes tests, benchmarks, evaluations, vendored benchmark code, Git metadata, graphs and caches. The source Git HEAD is informational: the package captures actual working-tree bytes, so commit and verify a stable checkout before release.

Extract into a staging directory, inspect the manifest, then place its `coding-team` directory in the personal `.agents/skills` directory while preserving an existing installation. The builder does not install, modify policy or change global instructions. It rejects linked operational resources before creating output and requires a filesystem supporting atomic hard-link publication. The complete `git archive` above remains useful for expert review and reproducible evidence; it intentionally includes benchmark/evaluation artifacts and is not a smaller runtime package.

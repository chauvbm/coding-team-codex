# Model routing

Read before delegation or when STRICT_MODEL applies. Model preferences have one source: [model-profiles.json](model-profiles.json). The active profile defaults to `runtime`; its null fields mean omit the override and inherit the host's supported defaults. Leader always stays on the current chat configuration.

## Resolve a dispatch

1. Resolve the role in the selected profile. An explicit task profile selection overrides the file's `active_profile` for that task without editing it. Unknown profiles/roles or malformed configuration are configuration errors: report them rather than silently interpreting them as runtime inheritance.
2. For each field, use an explicit user pin first, then a justified task-specific adaptive selection, then the selected role preference. Null means runtime inheritance, not an unknown model name to pass to the API. A configured preference is not a pin unless the user requires it or STRICT_MODEL applies. Under STRICT_MODEL, skip adaptive substitution of non-null configured fields; explicit user pins still take precedence.
3. Adapt only unpinned fields, within actual host capabilities, user budgets and restrictions. Prefer lighter settings for bounded investigation/mechanical work and stronger settings for difficult design/debugging or meaningful security, integrity and concurrency risks. Raise effort for a concrete unresolved reasoning problem; tool/credential failure alone is not a reason to select a stronger model. Skip delegation when direct work is more efficient.
4. Pass model/effort through supported structured fields. If overrides require fresh context, use that option with a self-contained handoff. Naming a model in a prompt does not select it. Do not edit runtime/global configuration to make a preference work.
5. Disclose an unavailable preference and use the runtime default unless STRICT_MODEL or an explicit exact pin forbids substitution. For a strict unavailable selection, report the constraint and request a choice while continuing independent work that does not depend on it. A null profile field imposes no exact model/effort requirement; it explicitly selects host inheritance even in STRICT_MODEL.

Identify the selected roles and material configuration choices. Distinguish requested fields from observed metadata: missing metadata means unverified, not a mismatch or verified selection. No token or speed saving is established merely by choosing a lighter model.

Reconfigure existing agents only through supported controls. Otherwise stop/await the former writer, inspect partial changes, transfer ownership and create a newly configured agent. Changed executors retain task history and allowances.

## Configure preferences once

Edit `active_profile` or the role mappings in the JSON only when the user requests persistent preference changes. Use the runtime profile unchanged for a portable installation. The optional `named_preferences` profile illustrates host-dependent preferences; select it only after checking available models/efforts. Names are examples, not availability guarantees. Role names are `Architect`, `Investigator`, `Developer`, `Test Engineer`, `QA / Reviewer`, and `Specialist`; FinalQA uses `QA / Reviewer`.

This JSON supplies instruction-level preferences. It neither installs models nor configures native agent profiles, and the governance numeric defaults remain separate.

After editing profiles, optionally check their structure before delegation with `python scripts/check_model_profiles.py` (or `--input <custom-file>`). The read-only checker returns JSON and exit 0 for valid structure, 2 for invalid/unreadable input. It rejects duplicate keys, missing/unknown roles or fields, invalid active profiles, and malformed model/effort values instead of silently treating them as inheritance. CI validates the shipped profiles too.

Schema v1 accepts null or a nonempty model name, and null or effort `low`, `medium`, `high`, `xhigh`, `max`, `ultra`. These are vocabulary checks only: a valid profile does not establish model access or effort support on the actual host. Confirm supported structured fields/capabilities at dispatch and retain the existing pin/fallback rules. A new host effort label requires an intentional schema/checker update, not silent substitution.

# Strict, transactional dotenv loading

This is one requested new-feature bundle on real python-dotenv source at commit
`bad5771ce54fd643538f177aab1465e4375e2039`, not a claim about an upstream bug.
Implement the complete contract below using the bundled standard-library-only
package. Preserve existing behavior when `strict` is omitted or false.

## Public interface and errors

Add a trailing optional `strict: bool = False` parameter to `DotEnv.__init__`,
`dotenv_values`, `load_dotenv`, `parser.parse_stream`, and
`variables.parse_variables`. Existing positional arguments remain compatible.
Export `DotEnvError` from both `dotenv.parser` and the package root; include it in
the root `__all__`. It subclasses `ValueError` and has these public attributes:

- `kind`: exactly `"parse"`, `"duplicate"`, or `"undefined"`.
- `line`: the failing binding's existing `binding.original.line` integer.
- `original`: the exact string in that binding's existing `binding.original.string`.

The error's human-readable message must include the kind and decimal line number;
its exact remaining wording is unrestricted. Keep the upstream parser's binding
boundaries, including leading blank whitespace and multiline quoted values. The
line number is the upstream binding start, which can precede its first token.

`variables.UndefinedVariableError` subclasses `ValueError` and exposes `.name`,
the missing reference name. This lower-level exception is contextualized as
`DotEnvError(kind="undefined", ...)` by strict `DotEnv` operations. Its exact
message is unrestricted. Do not expose implementation tracebacks as return values.

## Parser and interpolation

`parse_stream(stream, strict=True)` yields ordinary successful bindings, but raises
`DotEnvError(kind="parse", ...)` instead of yielding the first error binding. It
does not check duplicate keys. False/default mode retains recovery/error bindings.

`parse_variables(value, strict=True)` still yields atoms with `.resolve(mapping)`.
When resolving a recognized `${NAME}` with no `:-default`, a missing mapping key
raises `UndefinedVariableError(NAME)`. Missing means key absence, not a present
`None` or empty string; both present values expand to `""`. `${NAME:-default}`
retains upstream semantics: use the literal default only when the key is absent,
and expand present `None`/empty to `""`. No recursive expansion or new grammar is
requested. Literal `$NAME` and unrecognized syntax retain upstream behavior.
False/default mode retains upstream missing-reference expansion to `""`.
Atoms can be resolved repeatedly against different mappings without cached results.

## Integration and transaction boundary

Strict `DotEnv.dict()` and `dotenv_values` must fully parse and validate all
bindings, including valueless assignments. Reject the second definition of any
duplicate key with `kind="duplicate"` at that second binding. Check in source
order: the earliest offending binding wins. Within the same binding, precedence
is parse error, then duplicate key, then undefined reference. Comments/blank
bindings do not define keys.

For strict interpolation, capture one copy of `os.environ` at the beginning of an
uncached `DotEnv.dict()` computation, before reading its source. Resolve bindings
in source order, using only this snapshot and prior resolved file definitions.
With `override=True`, prior file definitions win; with `override=False`, the OS
snapshot wins. A key's own current definition is not available until its value
has resolved. Forward references are consequently missing unless present in the
snapshot. Preserve dictionary order and upstream valueless (`None`) results.
`dotenv_values` continues using `override=True`; `load_dotenv` keeps its existing
default `override=False`.

With `interpolate=False`, strict syntax/duplicate checks still apply, but variable
expressions remain literal and undefined references are not errors.

Strict `load_dotenv` and `DotEnv.set_as_environment_variables()` must finish all
parse/duplicate/undefined checks before making any environment assignment. On any
of these errors there must be zero environment writes, not writes followed by
rollback. Even a definition that will be skipped because `override=False` must
be validated, as must every duplicate occurrence. Successful commits retain
upstream skip/override, valueless and boolean-return behavior. Handling arbitrary
OS write failures, concurrent writers, invalid OS key/value characters, or
rollback after an OS write failure is outside this task's transaction guarantee.

A failed computation must not populate `DotEnv`'s successful-value cache. Existing
successful caching, source path/stream precedence, encoding, stream ownership,
missing-file behavior, disabled loading, and permissive warning/recovery behavior
remain intact. Do not change unrelated rewrite, CLI or IPython features.

You may modify the package and add your own tests. No external dependencies are
needed. The independent acceptance suite is held by the coordinator. Each run is
one attempt on this same bundle; repeated runs are not distinct task types.

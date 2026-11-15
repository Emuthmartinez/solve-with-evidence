# exec-04-settings-migration: fairness notes

The solver never sees this file, the grader or the exemplars.

## What the task is

Make `settings.store.load` read settings files written by every release, schema 1 (1.x) and schema 2 (2.x) as well as schema 3, by following a changelog written over eleven releases and the current schema document. `save` must keep writing schema 3.

## Why it is harder than the tasks it replaces

The replaced tasks gave one function and a complete numbered specification. Here the file-format rules are spread over `CHANGELOG.md`, where each one sits in a release entry beside unrelated UI notes, and the general rules sit in `docs/schema.md`. The rules interact: migration chains 1 to 2 to 3, two defaults changed between releases, a key's meaning depends on the schema the file declares and not on its name, and an older file must be valid in its own schema before it is migrated. The visible tests cover schema 3 only, and they pass on the starter and on every mistake below. The two expected fixtures pass for the bad exemplar too. Nothing in the prompt says which rules are easy to break.

## What the bad exemplar does

It is the first version a quick solver writes from the fixtures: each rename applied whenever the old key is present, whatever schema the file declares; the current defaults for every file; `int()` on any string timeout; the underscore in a locale replaced in every file, schema 3 included; `legacy_sync` dropped from every file; quiet hours split on `-` and `:` with no format check; and the migrated file written back to disk on load. It passes `test_store.py` and reproduces both files in `fixtures/expected/`.

## Hidden checks and the sentence each follows from

| Check | Stated rule | Where |
|---|---|---|
| schema 1 notify sets both notifications | "Migrating a schema 1 file sets both members to the old `notify` value." | `CHANGELOG.md`, 2.0.0 |
| schema 1 timeout seconds become milliseconds | "The schema 1 key `timeout`, in seconds, becomes `timeout_ms`, an integer: `"timeout": 45` becomes `"timeout_ms": 45000`." | `CHANGELOG.md`, 2.0.0 |
| older locales become hyphenated | "The schema 1 key `lang` is renamed `locale`, with the same value and the same form." (2.0.0) and "Migrating replaces the underscore with a hyphen." (3.0.0). `lang` is "two or three lowercase ASCII letters, optionally followed by `_` and two uppercase ASCII letters, such as `"en_US"` or `"fil"`" (1.0.0) | `CHANGELOG.md` |
| schema 3 locale must already be hyphenated | `locale` is "two or three lowercase ASCII letters, optionally followed by `-` and two uppercase ASCII letters"; "The result is checked against schema 3." Migration steps run only for the declared schema | `docs/schema.md`, Schema 3 and load steps 4 and 5 |
| missing timeout takes the default of its release | "A schema 1 file that never set `timeout` keeps the 30 seconds it had: it migrates to `"timeout_ms": 30000`." and "a schema 2 file without `timeout_ms` means 10000"; schema 3 default 10000 | `CHANGELOG.md`, 2.0.0; `docs/schema.md` table |
| missing theme takes the default of its release | "A schema 1 or schema 2 file without `theme` keeps `"light"`, the default of those releases." and "the schema 3 default for `appearance.theme` is `"system"`" | `CHANGELOG.md`, 3.0.0 |
| digit string timeout accepted in schema 1 | "A string `timeout` is read when it consists of one or more of the ASCII digits 0 to 9 and nothing else ..., and it means that many seconds, as the number would." | `CHANGELOG.md`, 1.3.1 |
| other timeout strings rejected | "(no sign, space, decimal point or underscore) ... Any other string `timeout` is an error, and so is a string `timeout_ms` in a schema 2 or schema 3 file." | `CHANGELOG.md`, 1.3.1 |
| migrated values are checked against schema 3 | "The result is checked against schema 3." and "A file that fails the check in step 3 or in step 5 raises `SettingsError`."; `timeout_ms` "an integer from 1000 to 600000"; "`true` and `false` are not integers, and `3.0` is not an integer. This holds in every schema." | `docs/schema.md` |
| values only schema 3 allows are rejected in older files | "The file is checked against the schema it declares, as the changelog defines that schema." with "Schema 1 and schema 2 allow only `"light"` and `"dark"`" (3.0.0), the `_` form of `lang` (1.0.0) and `locale` (2.0.0), and the string form of `quiet_hours` (2.2.0) | `docs/schema.md`, load step 3; `CHANGELOG.md` |
| quiet hours become minutes after midnight | "The schema 2 string `"HH:MM-HH:MM"` becomes `{"start": <minutes>, "end": <minutes>}` ... A missing or null schema 2 `quiet_hours` becomes `null`." and "an end earlier than the start means the range runs past midnight" | `CHANGELOG.md`, 3.0.0 and 2.2.0 |
| invalid quiet hours rejected | "a string `"HH:MM-HH:MM"`: the start time, a hyphen, and the end time, with no spaces or other characters, each time with a two-digit hour from 00 to 23, a colon and a two-digit minute from 00 to 59 ... The two times must differ" | `CHANGELOG.md`, 2.2.0 |
| high_contrast becomes the contrast | "schema 2 `"high_contrast": true` becomes `appearance.contrast` `"high"`, and `false` or a missing `high_contrast` becomes `"normal"`" | `CHANGELOG.md`, 3.0.0 |
| legacy_sync dropped from older files | "Schema 3 has no `legacy_sync` key, and migrating a schema 1 or schema 2 file drops it." | `CHANGELOG.md`, 3.0.0 |
| legacy_sync kept in a schema 3 file | "A top-level key is unknown when the schema that the file declares does not define it, even if another schema defines it." and "`load` returns each unknown key with its value unchanged" | `docs/schema.md`, Unknown keys |
| a schema 2 key stays unknown in a schema 1 file | The same two sentences, with "Which steps run depends on the declared schema alone, never on which keys the file happens to hold." `high_contrast` is a schema 2 key (2.5.0), not a schema 1 or schema 3 key | `docs/schema.md`; `CHANGELOG.md`, 2.5.0 |
| older keys stay unknown in newer files | The same sentences. `notify`, `lang` and `timeout` are not schema 2 keys; `theme`, `notify` and `high_contrast` are not schema 3 keys | `docs/schema.md`; `CHANGELOG.md` |
| an unknown key named like a schema 3 key is replaced | "When an unknown key has the name of a schema 3 key, the schema 3 value, migrated or default, replaces it." `notifications`, `timeout_ms` and `quiet_hours` are unknown in a schema 1 file | `docs/schema.md`, Unknown keys |
| unknown keys survive migration | "Unknown keys take no part in migration. `load` returns each unknown key with its value unchanged" | `docs/schema.md`, Unknown keys |
| partial nested objects take defaults | "Inside `notifications` and `appearance`, a missing member takes its default as well." and "a missing `notifications`, or a missing member, means `true`" | `docs/schema.md`, Schema 3; `CHANGELOG.md`, 2.0.0 |
| load does not write the file | "`load` never writes to disk." | `docs/schema.md`, Side effects |
| newer schema raises UnsupportedVersion | "An integer above 3 means a newer release wrote the file, and raises `UnsupportedVersion`." | `docs/schema.md`, load step 2 |
| malformed schema number raises SettingsError | "Any other value raises `SettingsError`: 0, a negative integer, `3.0`, `"3"`, `true`, `null`." and "`load` raises `UnsupportedVersion` only for an integer `schema` above 3." | `docs/schema.md`, load |
| not a JSON object raises SettingsError | "The file must hold a JSON object. Anything else raises `SettingsError`." | `docs/schema.md`, load step 1 |
| results share no state | "`load` never changes `DEFAULTS`. The dict it returns shares no object with `DEFAULTS` or with an earlier result, so the caller may change it freely." | `docs/schema.md`, Side effects |
| save writes migrated settings as schema 3 | "writes the full schema 3 object to `path`: `"schema": 3`, every schema 3 key, and every unknown key" | `docs/schema.md`, save |
| save leaves its argument unchanged | "`save` does not change `settings`." and "so may any key or member that has a default" | `docs/schema.md`, save |

Every hidden file is written into the grader's own temporary directory. The grader compares only the keys a check is about, so one mistake fails the checks for its own rule and not every check that loads a file.

`variants/exec-04-settings-migration.py` holds plausible mistakes, at least one per check. `test_bench.py` checks that each fails exactly the checks it lists.

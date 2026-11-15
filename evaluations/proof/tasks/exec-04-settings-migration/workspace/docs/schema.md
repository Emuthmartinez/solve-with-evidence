# The settings file

Tern keeps each user's settings in one JSON file, `settings.json`. `settings.store` reads it with `load(path)` and writes it with `save(path, settings)`.

This document defines schema 3, the format that release 3.0 and later write, and the rules `load` and `save` follow. `CHANGELOG.md` records the older formats. Schema 1 is the format of every 1.x release: the keys listed under 1.0.0 and 1.4.0. Schema 2 is the format of every 2.x release: the keys listed under 2.0.0, 2.2.0 and 2.5.0.

## Schema 3

The file holds a JSON object with these keys.

| Key | Value | Default |
|---|---|---|
| `schema` | The integer 3. | |
| `notifications` | An object with the members `email` and `push`, each `true` or `false`. | Both `true`. |
| `timeout_ms` | The network timeout in milliseconds: an integer from 1000 to 600000. | 10000 |
| `appearance` | An object with the members `theme`, one of `"light"`, `"dark"` or `"system"`, and `contrast`, one of `"normal"` or `"high"`. | `theme` `"system"`, `contrast` `"normal"`. |
| `locale` | The interface language: two or three lowercase ASCII letters, optionally followed by `-` and two uppercase ASCII letters, such as `"en-US"`, `"pt-BR"` or `"fil"`. | `"en-US"` |
| `quiet_hours` | `null`, or an object with exactly the members `start` and `end`, each an integer from 0 to 1439: minutes after midnight. | `null` |

- Every key except `schema` may be missing. A missing key takes its default.
- Inside `notifications` and `appearance`, a missing member takes its default as well. A member these objects do not define makes the file invalid.
- `start` and `end` must differ. `end` may be smaller than `start`, for quiet hours that run past midnight: 22:00 to 07:00 is `{"start": 1320, "end": 420}`.
- An integer is a JSON number written without a decimal point. `true` and `false` are not integers, and `3.0` is not an integer. This holds in every schema.

`settings.store.DEFAULTS` holds the defaults of schema 3. The preferences window shows them next to each setting.

## load(path)

1. The file must hold a JSON object. Anything else raises `SettingsError`.
2. The `schema` key names the schema the file declares. A file without a `schema` key is schema 1, because 1.x releases wrote no schema number. Otherwise `schema` must be an integer. 1, 2 and 3 are the schemas this release reads. An integer above 3 means a newer release wrote the file, and raises `UnsupportedVersion`. Any other value raises `SettingsError`: 0, a negative integer, `3.0`, `"3"`, `true`, `null`.
3. The file is checked against the schema it declares, as the changelog defines that schema.
4. The file is migrated one schema at a time, 1 to 2 and then 2 to 3, as the changelog describes each step. Which steps run depends on the declared schema alone, never on which keys the file happens to hold.
5. The result is checked against schema 3.
6. A file that fails the check in step 3 or in step 5 raises `SettingsError`.

`load` returns a dict in the schema 3 shape: `"schema": 3`, every schema 3 key with complete `notifications` and `appearance` objects, and the file's unknown keys.

`UnsupportedVersion` is a subclass of `SettingsError`, so code that catches `SettingsError` catches both. `load` raises `UnsupportedVersion` only for an integer `schema` above 3.

The rules in the list under "Schema 3" about missing keys, missing members and integers apply to schema 1 and schema 2 files too.

### Defaults in older files

A key missing from an older file takes the default of the release that wrote the file, not the current default. The changelog records each default that changed.

### Unknown keys

A top-level key is unknown when the schema that the file declares does not define it, even if another schema defines it. Unknown keys take no part in migration. `load` returns each unknown key with its value unchanged, and `save` writes it back, so a setting from a plugin or from a newer release survives a round trip through this one.

A file can hold a key from a newer schema when a newer release wrote it and an older release later saved it again, keeping the keys it did not know. When an unknown key has the name of a schema 3 key, the schema 3 value, migrated or default, replaces it.

### Side effects

`load` never writes to disk. A file stays as the release that wrote it left it until the app calls `save`.

`load` never changes `DEFAULTS`. The dict it returns shares no object with `DEFAULTS` or with an earlier result, so the caller may change it freely.

## save(path, settings)

`settings` is a dict in the schema 3 shape, such as one that `load` returned. Its `schema` key may be missing, and so may any key or member that has a default. `save` checks it as `load` checks a schema 3 file, raises `SettingsError` if it fails, and otherwise writes the full schema 3 object to `path`: `"schema": 3`, every schema 3 key, and every unknown key. `save` does not change `settings`.

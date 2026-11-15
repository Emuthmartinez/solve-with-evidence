# Changelog

Notable changes to Tern, newest first.

## 3.0.0 (2026-09-14)

### Changed

- New look: rounded panels, a calmer color palette and larger click targets in the toolbar.
- The settings file moves to schema 3, with `"schema": 3`. This release reads files from every earlier release and writes schema 3 the next time settings are saved.
- The theme setting moves into a new `appearance` object: the schema 2 `theme` value becomes `appearance.theme`.
- The high contrast setting moves into `appearance` too: schema 2 `"high_contrast": true` becomes `appearance.contrast` `"high"`, and `false` or a missing `high_contrast` becomes `"normal"`.
- Locales are written with a hyphen, as the operating system writes them: where schema 2 had `"locale": "pt_BR"`, schema 3 has `"locale": "pt-BR"`. Migrating replaces the underscore with a hyphen.
- Quiet hours are stored as minutes after midnight. The schema 2 string `"HH:MM-HH:MM"` becomes `{"start": <minutes>, "end": <minutes>}`: `"08:15-12:00"` becomes `{"start": 495, "end": 720}`. A missing or null schema 2 `quiet_hours` becomes `null`.

### Added

- A System theme that follows the operating system's light or dark mode. `appearance.theme` may be `"system"` in schema 3. Schema 1 and schema 2 allow only `"light"` and `"dark"`.
- New installs use the System theme, so the schema 3 default for `appearance.theme` is `"system"`. A schema 1 or schema 2 file without `theme` keeps `"light"`, the default of those releases.
- Search inside attachments.

### Removed

- Legacy cloud sync, deprecated in 2.4.0. Schema 3 has no `legacy_sync` key, and migrating a schema 1 or schema 2 file drops it.
- Support for Windows 7 and macOS 10.14.

### Fixed

- The app no longer freezes for a few seconds when it wakes from sleep.

## 2.6.0 (2026-02-03)

### Added

- Export a report as PDF.

### Fixed

- The main window no longer opens off screen after an external monitor is unplugged.
- Drag and drop of several files at once no longer drops all but the first.

## 2.5.0 (2025-10-20)

### Added

- High contrast mode, in Preferences > Appearance. Schema 2 files can now hold `high_contrast`, `true` or `false`. A missing `high_contrast` means `false`.
- Ctrl+K opens search from anywhere.

## 2.4.1 (2025-08-11)

### Fixed

- A crash when a report title held an emoji.

## 2.4.0 (2025-07-28)

### Changed

- Startup is about twice as fast on large libraries.

### Deprecated

- Legacy cloud sync. It will be removed in 3.0. Use the new sync in Preferences > Accounts.

## 2.3.0 (2025-05-06)

### Added

- Tabs can be reordered by dragging.
- Spell checking in notes.

## 2.2.0 (2025-02-17)

### Added

- Quiet hours: no push notifications during a daily time range, in Preferences > Notifications. Schema 2 files can now hold `quiet_hours`, a string `"HH:MM-HH:MM"`: the start time, a hyphen, and the end time, with no spaces or other characters, each time with a two-digit hour from 00 to 23, a colon and a two-digit minute from 00 to 59, such as `"22:30-07:00"`. The two times must differ, and an end earlier than the start means the range runs past midnight. A missing or null `quiet_hours` means no quiet hours.

### Fixed

- Notifications for the same event no longer arrive twice.

## 2.1.0 (2024-12-02)

### Added

- A dark icon for the menu bar.

## 2.0.0 (2024-10-07)

### Changed

- The settings file now starts with a schema number, `"schema": 2`. A file without one is schema 1, written by a 1.x release. From this release on, readers choose the migration steps for a file by its schema number alone, never by looking at which keys it holds.
- Notifications can be turned on separately for email and push. The schema 1 key `notify` becomes the object `notifications`, with the members `email` and `push`, each `true` or `false`; a missing `notifications`, or a missing member, means `true`. Migrating a schema 1 file sets both members to the old `notify` value.
- The network timeout is stored in milliseconds. The schema 1 key `timeout`, in seconds, becomes `timeout_ms`, an integer: `"timeout": 45` becomes `"timeout_ms": 45000`.
- The default network timeout drops from 30 seconds to 10 seconds, so a schema 2 file without `timeout_ms` means 10000. A schema 1 file that never set `timeout` keeps the 30 seconds it had: it migrates to `"timeout_ms": 30000`.
- The schema 1 key `lang` is renamed `locale`, with the same value and the same form. A missing `locale` means `"en_US"`.
- `theme` and `legacy_sync` keep their names, values and defaults.
- A redesigned Preferences window.

## 1.5.0 (2024-04-15)

### Added

- Reports can be pinned to the sidebar.

### Fixed

- Sorting by date put items from the 1st of a month last.

## 1.4.0 (2023-11-20)

### Added

- Legacy cloud sync, in Preferences > Sync. The settings file can now hold `legacy_sync`, `true` or `false`. A missing `legacy_sync` means `false`.

## 1.3.1 (2023-08-09)

### Fixed

- 1.3.0 saved `timeout` as a string of digits, such as `"timeout": "45"`, instead of a number. 1.3.1 saves a number again and reads files that hold such a string, and so does every later release, for files without a schema number only. A string `timeout` is read when it consists of one or more of the ASCII digits 0 to 9 and nothing else (no sign, space, decimal point or underscore), and it means that many seconds, as the number would. Any other string `timeout` is an error, and so is a string `timeout_ms` in a schema 2 or schema 3 file.

## 1.3.0 (2023-07-24)

### Added

- The network timeout can be changed in Preferences > Network.

## 1.2.0 (2023-03-13)

### Added

- Keyboard shortcuts for switching tabs.

### Fixed

- The window title showed the wrong file name after a rename.

## 1.1.0 (2022-11-28)

### Added

- Attachments can be previewed without opening them.

## 1.0.0 (2022-09-05)

First release. Settings are saved in `settings.json`, a JSON object with these keys, each optional:

- `notify`: `true` or `false`, whether to show notifications. Default `true`.
- `timeout`: the network timeout in whole seconds, an integer. Default 30.
- `theme`: `"light"` or `"dark"`. Default `"light"`.
- `lang`: the interface language: two or three lowercase ASCII letters, optionally followed by `_` and two uppercase ASCII letters, such as `"en_US"` or `"fil"`. Default `"en_US"`.
